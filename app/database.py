"""
Engine do SQLAlchemy + sessão por request.

Guarda só os dados de login dos professores. Por padrão usa SQLite (um
arquivo só, zero configuração de servidor) — suficiente pra um punhado de
professores. Se um dia quiserem centralizar num Postgres só (ex: o mesmo
Supabase do Saldo+), basta trocar o DATABASE_URL no .env; nada no código
muda.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# check_same_thread só é necessário pro SQLite (o FastAPI atende requests em
# threads diferentes); um Postgres/pg8000 não precisa disso.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
