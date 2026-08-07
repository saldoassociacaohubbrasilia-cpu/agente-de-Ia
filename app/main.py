"""Ponto de entrada da API. Local: uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import auth_router, chat_router, relatorios_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria as tabelas (professores, chamados, planilhas) se ainda não
    # existirem. Não mexe no banco vetorial — isso é feito pelo script de
    # ingestão, separadamente.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Agente de IA — Suporte a Professores",
    description="Assistente pedagógico com RAG, abertura de chamado e relatório básico de turma.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(chat_router.router, prefix="/api/v1")
app.include_router(relatorios_router.router, prefix="/api/v1")
