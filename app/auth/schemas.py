"""Formatos de entrada/saída das rotas de autenticação."""
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TeacherOut(BaseModel):
    username: str
    full_name: str
    school: str | None = None

    model_config = {"from_attributes": True}
