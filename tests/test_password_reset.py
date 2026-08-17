"""
Teste de fumaça do fluxo de "esqueci minha senha": pede o reset, confere
que um token foi gravado, redefine a senha com ele e confirma que o login
antigo para de funcionar e o novo passa a funcionar. SMTP inválido no
ambiente de teste (ver tests/test_auth.py) — o envio de e-mail falha e é
só um aviso no console, igual acontece com abertura de chamado.

Rodar com: pytest
"""
import os

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

from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.auth.security import get_password_hash  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import PasswordResetToken, Teacher  # noqa: E402

USUARIO = "professor.reset"


def _preparar_professor() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(PasswordResetToken).filter(PasswordResetToken.teacher_username == USUARIO).delete()
        if not db.query(Teacher).filter(Teacher.username == USUARIO).first():
            db.add(
                Teacher(
                    username=USUARIO,
                    full_name="Professor Reset",
                    email="professor.reset@escola.com",
                    hashed_password=get_password_hash("senha_antiga"),
                )
            )
        else:
            db.query(Teacher).filter(Teacher.username == USUARIO).update(
                {"hashed_password": get_password_hash("senha_antiga")}
            )
        db.commit()
    finally:
        db.close()


def test_esqueci_senha_gera_token_e_nao_revela_se_usuario_existe():
    _preparar_professor()
    client = TestClient(app)

    resposta_existente = client.post("/api/v1/esqueci-senha", json={"usuario": USUARIO})
    assert resposta_existente.status_code == 204

    resposta_inexistente = client.post("/api/v1/esqueci-senha", json={"usuario": "nao.existe.jamais"})
    assert resposta_inexistente.status_code == 204  # mesma resposta, não revela nada

    db = SessionLocal()
    try:
        token_gravado = db.query(PasswordResetToken).filter(PasswordResetToken.teacher_username == USUARIO).first()
    finally:
        db.close()
    assert token_gravado is not None


def test_redefinir_senha_com_token_valido_troca_a_senha():
    _preparar_professor()
    client = TestClient(app)
    client.post("/api/v1/esqueci-senha", json={"usuario": USUARIO})

    db = SessionLocal()
    try:
        token = db.query(PasswordResetToken).filter(PasswordResetToken.teacher_username == USUARIO).first().token
    finally:
        db.close()

    resposta = client.post("/api/v1/redefinir-senha", json={"token": token, "nova_senha": "senha_nova_123"})
    assert resposta.status_code == 204

    # senha antiga não funciona mais
    login_antigo = client.post("/api/v1/login", data={"username": USUARIO, "password": "senha_antiga"})
    assert login_antigo.status_code == 401

    # senha nova funciona
    login_novo = client.post("/api/v1/login", data={"username": USUARIO, "password": "senha_nova_123"})
    assert login_novo.status_code == 200

    # token é de uso único — usar de novo falha
    reuso = client.post("/api/v1/redefinir-senha", json={"token": token, "nova_senha": "outra_senha_456"})
    assert reuso.status_code == 400


def test_redefinir_senha_com_token_invalido_ou_expirado():
    _preparar_professor()
    client = TestClient(app)

    resposta_invalido = client.post(
        "/api/v1/redefinir-senha", json={"token": "token-que-nao-existe", "nova_senha": "senha_nova_123"}
    )
    assert resposta_invalido.status_code == 400

    db = SessionLocal()
    try:
        db.add(
            PasswordResetToken(
                teacher_username=USUARIO,
                token="token-ja-expirado",
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        db.commit()
    finally:
        db.close()

    resposta_expirado = client.post(
        "/api/v1/redefinir-senha", json={"token": "token-ja-expirado", "nova_senha": "senha_nova_123"}
    )
    assert resposta_expirado.status_code == 400
