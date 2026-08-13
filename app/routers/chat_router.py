"""Rota protegida de chat. Só responde se o token JWT enviado for válido."""
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.security import get_current_teacher
from app.database import get_db
from app.models import Conversa, Mensagem, Teacher
from app.rag.chain import answer_question

router = APIRouter(tags=["chat"])

TAMANHO_MAX_TITULO = 60


class ChatRequest(BaseModel):
    pergunta: str = Field(..., min_length=3, max_length=2000)
    # se vazio, cria uma conversa nova; se preenchido, continua uma existente
    conversa_id: int | None = None


class Fonte(BaseModel):
    arquivo: str
    pagina: int | None = None


class ChatResponse(BaseModel):
    resposta: str
    fontes: list[Fonte]
    chamado_id: int | None = None  # preenchido quando o agente abriu um chamado de suporte nessa resposta
    conversa_id: int  # pro front continuar mandando nas próximas perguntas dessa mesma conversa


def get_answer_fn() -> Callable[[str, Teacher, Session], dict]:
    """
    Indireção só pra facilitar teste: nos testes automatizados dá pra
    sobrescrever essa dependency (app.dependency_overrides) e simular uma
    resposta do RAG sem precisar de chave de API real nem do Qdrant no ar.
    """
    return answer_question


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
    answer_fn: Callable[[str, Teacher, Session], dict] = Depends(get_answer_fn),
) -> ChatResponse:
    if payload.conversa_id is not None:
        conversa = (
            db.query(Conversa)
            .filter(Conversa.id == payload.conversa_id, Conversa.teacher_username == current_teacher.username)
            .first()
        )
        if conversa is None:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
    else:
        titulo = payload.pergunta[:TAMANHO_MAX_TITULO]
        if len(payload.pergunta) > TAMANHO_MAX_TITULO:
            titulo += "…"
        conversa = Conversa(teacher_username=current_teacher.username, titulo=titulo)
        db.add(conversa)
        db.flush()  # gera conversa.id sem precisar commitar ainda

    resultado = answer_fn(payload.pergunta, current_teacher, db)

    db.add(Mensagem(conversa_id=conversa.id, autor="professor", texto=payload.pergunta))
    db.add(
        Mensagem(
            conversa_id=conversa.id,
            autor="agente",
            texto=resultado["resposta"],
            fontes=resultado["fontes"],
            chamado_id=resultado.get("chamado_id"),
        )
    )
    db.commit()

    return ChatResponse(**resultado, conversa_id=conversa.id)
