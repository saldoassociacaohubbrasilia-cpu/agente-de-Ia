"""
Testes das duas ferramentas novas:

1. abrir_chamado -> grava no banco mesmo se o e-mail falhar (SMTP fake).
2. _resumir_planilha -> lê uma planilha salva como bytes e calcula as
   estatísticas básicas certas.
3. O loop de tool-calling em app/rag/chain.answer_question -> testado com um
   LLM "dublê" que simula o Claude pedindo pra chamar a ferramenta de
   chamado, sem precisar de chave de API real nem de rede.

Rodar com: pytest
"""
import io
import os

os.environ.setdefault("SECRET_KEY", "chave-de-teste")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_teachers.db")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("QDRANT_API_KEY", "chave-de-teste")
os.environ.setdefault("ANTHROPIC_API_KEY", "chave-de-teste")
os.environ.setdefault("OPENAI_API_KEY", "chave-de-teste")
os.environ.setdefault("SMTP_HOST", "smtp.invalido.teste")
os.environ.setdefault("SMTP_USER", "teste@teste.com")
os.environ.setdefault("SMTP_PASSWORD", "chave-de-teste")
os.environ.setdefault("SMTP_FROM", "teste@teste.com")
os.environ.setdefault("SUPPORT_EMAIL_TO", "suporte@teste.com")

import pandas as pd  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402

from app.auth.security import get_password_hash  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Planilha, Teacher  # noqa: E402
from app.rag.relatorios import _resumir_planilha  # noqa: E402
from app.support.tickets import abrir_chamado  # noqa: E402


def _db_limpo():
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def _professor(db, turma="3A"):
    professor = Teacher(
        username=f"prof.{turma}",
        full_name="Professora Teste",
        email="professora@escola.com",
        turma=turma,
        hashed_password="x",
    )
    if not db.query(Teacher).filter(Teacher.username == professor.username).first():
        db.add(professor)
        db.commit()
        db.refresh(professor)
    return professor


# --- 1. Abrir chamado ---------------------------------------------------


def test_abrir_chamado_salva_mesmo_com_smtp_indisponivel():
    db = _db_limpo()
    professor = _professor(db)

    ticket = abrir_chamado(db, professor, pergunta="Meu login não funciona", resumo="Problema de acesso à conta")

    assert ticket.id is not None
    assert ticket.status == "aberto"
    assert ticket.teacher_username == professor.username
    assert "login" in ticket.pergunta.lower()
    db.close()


# --- 2. Resumo de planilha ------------------------------------------------


def test_resumir_planilha_filtra_por_turma_e_calcula_estatisticas():
    db = _db_limpo()
    professor = _professor(db, turma="3A")

    df = pd.DataFrame(
        {
            "aluno": ["Ana", "Bruno", "Carla", "Davi"],
            "turma": ["3A", "3A", "3B", "3A"],
            "progresso": [80, 45, 90, 10],
            "dias_sem_acesso": [1, 15, 0, 30],
        }
    )
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)

    db.add(Planilha(filename="turmas.xlsx", conteudo=buffer.getvalue(), uploaded_by=professor.username))
    db.commit()

    resumo = _resumir_planilha(db, professor)

    assert resumo is not None
    assert resumo["total_linhas"] == 3  # só as 3 linhas da turma 3A
    assert "progresso" in resumo["estatisticas_numericas"]
    assert resumo["estatisticas_numericas"]["progresso"]["mean"] == 45.0  # (80+45+10)/3
    db.close()


# --- 3. Loop de tool-calling em chain.answer_question ----------------------


class _LLMFalso:
    """Simula ChatAnthropic: bind_tools devolve ele mesmo, invoke consome uma lista de respostas roteirizadas."""

    def __init__(self, respostas):
        self._respostas = list(respostas)

    def bind_tools(self, tools):
        return self

    def invoke(self, mensagens):
        return self._respostas.pop(0)


class _VectorstoreFalso:
    def similarity_search(self, question, k):
        return []  # sem trecho relevante -> força o cenário de "problema real, abre chamado"


def test_answer_question_abre_chamado_quando_llm_decide(monkeypatch):
    db = _db_limpo()
    professor = _professor(db, turma="9B")

    respostas_roteirizadas = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "abrir_chamado_de_suporte",
                    "args": {"resumo": "Professora não consegue acessar a conta"},
                    "id": "call_1",
                }
            ],
        ),
        AIMessage(content="Abri um chamado pra você, a equipe entra em contato em breve.", tool_calls=[]),
    ]

    monkeypatch.setattr("app.rag.chain.ChatAnthropic", lambda **kwargs: _LLMFalso(respostas_roteirizadas))
    monkeypatch.setattr("app.rag.chain.get_vectorstore", lambda: _VectorstoreFalso())

    from app.rag.chain import answer_question

    resultado = answer_question("Não consigo entrar no sistema, o que eu faço?", professor, db)

    assert resultado["chamado_id"] is not None
    assert "chamado" in resultado["resposta"].lower()

    # confirma que o chamado realmente foi gravado no banco, não só reportado na resposta
    from app.models import Ticket

    ticket = db.query(Ticket).filter(Ticket.id == resultado["chamado_id"]).first()
    assert ticket is not None
    assert ticket.teacher_username == professor.username
    db.close()


# --- 4. Upload de planilha, de ponta a ponta (via HTTP de verdade) --------


def test_upload_planilha_via_api():
    db = _db_limpo()
    if not db.query(Teacher).filter(Teacher.username == "prof.upload").first():
        db.add(
            Teacher(
                username="prof.upload",
                full_name="Professora Upload",
                email="upload@escola.com",
                turma="7C",
                hashed_password=get_password_hash("senha123"),
            )
        )
        db.commit()
    db.close()

    client = TestClient(app)
    login = client.post("/api/v1/login", data={"username": "prof.upload", "password": "senha123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    df = pd.DataFrame({"aluno": ["Ana", "Bruno"], "turma": ["7C", "7C"], "progresso": [70, 90]})
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    resposta = client.post(
        "/api/v1/planilhas",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "arquivo": (
                "turmas_upload.xlsx",
                buffer,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert resposta.status_code == 200
    assert "recebida" in resposta.json()["mensagem"]

    # confere que a planilha foi mesmo pro banco, e não só um 200 vazio
    db = SessionLocal()
    salva = db.query(Planilha).filter(Planilha.filename == "turmas_upload.xlsx").first()
    assert salva is not None
    assert salva.uploaded_by == "prof.upload"
    db.close()


def test_upload_planilha_rejeita_extensao_invalida():
    client = TestClient(app)
    login = client.post("/api/v1/login", data={"username": "prof.upload", "password": "senha123"})
    token = login.json()["access_token"]

    resposta = client.post(
        "/api/v1/planilhas",
        headers={"Authorization": f"Bearer {token}"},
        files={"arquivo": ("nota.txt", io.BytesIO(b"nao e planilha"), "text/plain")},
    )
    assert resposta.status_code == 400
