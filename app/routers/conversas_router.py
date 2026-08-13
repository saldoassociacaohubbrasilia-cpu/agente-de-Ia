"""
Rotas de histórico de conversas — listar e detalhar as conversas do
professor logado. A criação de conversas em si acontece em chat_router.py
(a primeira pergunta já cria a conversa).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.security import get_current_teacher
from app.database import get_db
from app.models import Conversa, Teacher
from app.routers.chat_router import Fonte

router = APIRouter(tags=["conversas"])


class ConversaResumo(BaseModel):
    id: int
    titulo: str
    criada_em: datetime = Field(validation_alias="created_at")

    model_config = {"from_attributes": True, "populate_by_name": True}


class MensagemOut(BaseModel):
    id: int
    autor: str
    texto: str
    fontes: list[Fonte] | None = None
    chamado_id: int | None = None
    criada_em: datetime = Field(validation_alias="created_at")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ConversaDetalhe(BaseModel):
    id: int
    titulo: str
    criada_em: datetime = Field(validation_alias="created_at")
    mensagens: list[MensagemOut]

    model_config = {"from_attributes": True, "populate_by_name": True}


@router.get("/conversas", response_model=list[ConversaResumo])
def listar_conversas(
    current_teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)
) -> list[Conversa]:
    """Lista as conversas do professor logado, mais recente primeiro — usado pra montar o histórico da lateral."""
    return (
        db.query(Conversa)
        .filter(Conversa.teacher_username == current_teacher.username)
        .order_by(Conversa.created_at.desc())
        .all()
    )


@router.get("/conversas/{conversa_id}", response_model=ConversaDetalhe)
def detalhar_conversa(
    conversa_id: int, current_teacher: Teacher = Depends(get_current_teacher), db: Session = Depends(get_db)
) -> Conversa:
    """Mensagens de uma conversa. 404 se não existir OU se pertencer a outro professor — nunca revela qual dos dois."""
    conversa = (
        db.query(Conversa)
        .filter(Conversa.id == conversa_id, Conversa.teacher_username == current_teacher.username)
        .first()
    )
    if conversa is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return conversa
