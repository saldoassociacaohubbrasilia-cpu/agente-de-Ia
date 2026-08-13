"""Formatos de entrada/saída das rotas de autenticação."""
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TeacherOut(BaseModel):
    # username/password em POST /login são exigência do padrão OAuth2 (o
    # FastAPI/Swagger espera esses nomes exatos) — mas o retorno de /me é
    # nosso, então os campos saem em português. validation_alias lê do
    # atributo em inglês do model SQLAlchemy (Teacher.username etc).
    usuario: str = Field(validation_alias="username")
    nome_completo: str = Field(validation_alias="full_name")
    escola: str | None = Field(default=None, validation_alias="school")

    model_config = {"from_attributes": True, "populate_by_name": True}
