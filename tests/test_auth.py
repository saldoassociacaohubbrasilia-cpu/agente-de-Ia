"""
Teste de fumaça: sobe a API com um SQLite temporário, cadastra um professor
direto no banco, e testa /login e /chat — com a resposta do RAG "dublada"
(sem precisar de chave de API real nem do Qdrant no ar pra rodar o teste).

Rodar com: pytest
"""
import os

# Precisa existir ANTES de qualquer `from app...` (o Settings lê no import).
os.environ.setdefault("SECRET_KEY", "chave-de-teste")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_teachers.db")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("QDRANT_API_KEY", "chave-de-teste")
os.environ.setdefault("GOOGLE_API_KEY", "chave-de-teste")
os.environ.setdefault("SMTP_HOST", "smtp.invalido.teste")
os.environ.setdefault("SMTP_USER", "teste@teste.com")
os.environ.setdefault("SMTP_PASSWORD", "chave-de-teste")
os.environ.setdefault("SMTP_FROM", "teste@teste.com")
os.environ.setdefault("SUPPORT_EMAIL_TO", "suporte@teste.com")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth.security import get_password_hash  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Teacher  # noqa: E402
from app.routers.chat_router import get_answer_fn  # noqa: E402


def _preparar_professor_de_teste() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(Teacher).filter(Teacher.username == "professor.teste").first():
            db.add(
                Teacher(
                    username="professor.teste",
                    full_name="Professor Teste",
                    email="professor.teste@escola.com",
                    turma="3A",
                    hashed_password=get_password_hash("senha123"),
                )
            )
            db.commit()
    finally:
        db.close()


def _resposta_falsa(pergunta: str, teacher, db) -> dict:
    return {
        "resposta": f"Resposta simulada para: {pergunta}",
        "fontes": [{"arquivo": "manual.pdf", "pagina": 3}],
        "chamado_id": None,
    }


def test_login_e_chat_com_e_sem_token():
    _preparar_professor_de_teste()
    app.dependency_overrides[get_answer_fn] = lambda: _resposta_falsa
    client = TestClient(app)

    # login com credenciais certas
    resposta_login = client.post(
        "/api/v1/login", data={"username": "professor.teste", "password": "senha123"}
    )
    assert resposta_login.status_code == 200
    token = resposta_login.json()["access_token"]

    # login com senha errada
    login_errado = client.post(
        "/api/v1/login", data={"username": "professor.teste", "password": "errada"}
    )
    assert login_errado.status_code == 401

    # chat sem token -> bloqueado
    sem_token = client.post("/api/v1/chat", json={"pergunta": "Como faço uma avaliação diagnóstica?"})
    assert sem_token.status_code == 401

    # chat com token -> passa e usa a resposta "dublada"
    com_token = client.post(
        "/api/v1/chat",
        json={"pergunta": "Como faço uma avaliação diagnóstica?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert com_token.status_code == 200
    corpo = com_token.json()
    assert "Resposta simulada" in corpo["resposta"]
    assert corpo["fontes"][0]["arquivo"] == "manual.pdf"
    assert corpo["chamado_id"] is None

    app.dependency_overrides.clear()
