"""
Tudo relacionado a senha e token JWT.

Fluxo: professor manda usuário+senha em POST /api/v1/login -> confere hash
da senha -> gera um token JWT que expira em ACCESS_TOKEN_EXPIRE_MINUTES ->
professor manda esse token no header Authorization em toda chamada pra
/api/v1/chat -> get_current_teacher confere o token e busca o professor no
banco a cada request.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Teacher

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl aponta pro caminho real de login — é só o que aparece documentado
# no Swagger (/docs), o FastAPI não chama essa URL sozinho.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def authenticate_teacher(db: Session, username: str, password: str) -> Teacher | None:
    teacher = db.query(Teacher).filter(Teacher.username == username, Teacher.is_active.is_(True)).first()
    if teacher is None or not verify_password(password, teacher.hashed_password):
        return None
    return teacher


CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não foi possível validar as credenciais",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_teacher(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Teacher:
    """Dependency usada em toda rota protegida — troca o token JWT pelo professor dono dele."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise CREDENTIALS_ERROR
    except JWTError as exc:
        raise CREDENTIALS_ERROR from exc

    teacher = db.query(Teacher).filter(Teacher.username == username).first()
    if teacher is None or not teacher.is_active:
        raise CREDENTIALS_ERROR
    return teacher
