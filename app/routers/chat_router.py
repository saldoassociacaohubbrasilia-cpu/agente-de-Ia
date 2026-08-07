"""Rota protegida de chat. Só responde se o token JWT enviado for válido."""
from typing import Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.security import get_current_teacher
from app.database import get_db
from app.models import Teacher
from app.rag.chain import answer_question

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    pergunta: str = Field(..., min_length=3, max_length=2000)


class Fonte(BaseModel):
    arquivo: str
    pagina: int | None = None


class ChatResponse(BaseModel):
    resposta: str
    fontes: list[Fonte]
    chamado_id: int | None = None  # preenchido quando o agente abriu um chamado de suporte nessa resposta


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
    resultado = answer_fn(payload.pergunta, current_teacher, db)
    return ChatResponse(**resultado)
