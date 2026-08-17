"""Rota de login. É a única porta de entrada que não exige token."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.password_reset import redefinir_senha, solicitar_reset
from app.auth.schemas import EsqueciSenhaRequest, RedefinirSenhaRequest, TeacherOut, Token
from app.auth.security import authenticate_teacher, create_access_token, get_current_teacher
from app.database import get_db
from app.models import Teacher

router = APIRouter(tags=["autenticação"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    """
    Recebe usuário/senha como form-data (padrão OAuth2, é o que o Swagger e
    qualquer client HTTP esperam) e devolve um token JWT.
    """
    teacher = authenticate_teacher(db, form_data.username, form_data.password)
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=teacher.username)
    return Token(access_token=token)


@router.get("/me", response_model=TeacherOut)
def me(current_teacher: Teacher = Depends(get_current_teacher)) -> Teacher:
    """Útil pro frontend confirmar que o token ainda é válido e mostrar o nome do professor logado."""
    return current_teacher


@router.post("/esqueci-senha", status_code=status.HTTP_204_NO_CONTENT)
def esqueci_senha(payload: EsqueciSenhaRequest, db: Session = Depends(get_db)) -> None:
    """
    Sempre devolve 204, exista ou não o usuário — do contrário essa rota
    vira uma forma de descobrir quem está cadastrado no sistema.
    """
    solicitar_reset(db, payload.usuario)


@router.post("/redefinir-senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha_rota(payload: RedefinirSenhaRequest, db: Session = Depends(get_db)) -> None:
    if not redefinir_senha(db, payload.token, payload.nova_senha):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Link inválido ou expirado. Peça um novo."
        )
