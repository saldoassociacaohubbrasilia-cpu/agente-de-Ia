"""
Fluxo de "esqueci minha senha": gera um token de uso único, manda por
e-mail um link pro frontend redefinir, e troca a senha quando esse token
volta válido. Reaproveita o mesmo SMTP já usado pra abertura de chamado
(app/support/tickets.py).
"""
import smtplib
import secrets
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.auth.security import get_password_hash
from app.config import get_settings
from app.models import PasswordResetToken, Teacher

settings = get_settings()


def _enviar_email_reset(teacher: Teacher, token: str) -> None:
    # Query param na raiz (não um path próprio) pra funcionar em qualquer
    # hospedagem estática (GitHub Pages, Vercel, Netlify) sem precisar
    # configurar fallback de rota de SPA.
    link = f"{settings.FRONTEND_URL}/?token={token}"
    corpo = (
        f"Olá, {teacher.full_name}!\n\n"
        "Recebemos um pedido pra redefinir sua senha do Agente de IA de Suporte a Professores.\n\n"
        f"Clique no link abaixo pra escolher uma senha nova (válido por "
        f"{settings.RESET_TOKEN_EXPIRE_MINUTES} minutos):\n{link}\n\n"
        "Se você não pediu isso, é só ignorar este e-mail — sua senha continua a mesma."
    )
    msg = MIMEText(corpo, _charset="utf-8")
    msg["Subject"] = "Redefinição de senha — Agente de IA de Suporte a Professores"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = teacher.email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def solicitar_reset(db: Session, usuario: str) -> None:
    """
    Não revela se o usuário existe (evita que alguém use essa rota pra
    descobrir quem está cadastrado) — por isso não devolve nada, e segue em
    silêncio quando o usuário não existe ou está inativo.
    """
    teacher = db.query(Teacher).filter(Teacher.username == usuario, Teacher.is_active.is_(True)).first()
    if teacher is None:
        return

    # invalida qualquer token anterior ainda não usado, pra só o mais
    # recente pedido funcionar
    db.query(PasswordResetToken).filter(PasswordResetToken.teacher_username == teacher.username).delete()

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
    db.add(PasswordResetToken(teacher_username=teacher.username, token=token, expires_at=expires_at))
    db.commit()

    try:
        _enviar_email_reset(teacher, token)
    except Exception as exc:  # não deixa o request quebrar só porque o SMTP falhou
        print(f"[aviso] token de reset gerado pra {teacher.username}, mas o e-mail falhou: {exc}")


def redefinir_senha(db: Session, token: str, nova_senha: str) -> bool:
    """Troca a senha se o token existir e ainda for válido. Devolve False pra token inexistente/expirado."""
    registro = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    if registro is None:
        return False

    expira_em = registro.expires_at
    if expira_em.tzinfo is None:  # SQLite guarda datetime sem timezone
        expira_em = expira_em.replace(tzinfo=timezone.utc)
    if expira_em < datetime.now(timezone.utc):
        db.delete(registro)
        db.commit()
        return False

    teacher = db.query(Teacher).filter(Teacher.username == registro.teacher_username).first()
    if teacher is None:
        db.delete(registro)
        db.commit()
        return False

    teacher.hashed_password = get_password_hash(nova_senha)
    db.delete(registro)  # uso único
    db.commit()
    return True
