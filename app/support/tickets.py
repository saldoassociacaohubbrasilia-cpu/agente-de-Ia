"""
Abertura de chamados: quando o agente decide que uma dúvida precisa de
acompanhamento humano, isso aqui grava o registro no banco e manda um
e-mail pra equipe de suporte.

O registro no banco fica SEMPRE, mesmo que o envio do e-mail falhe (rede
fora do ar, credencial SMTP errada etc.) — melhor um chamado sem e-mail do
que um chamado perdido.
"""
import smtplib
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Teacher, Ticket

settings = get_settings()


def _enviar_email(ticket: Ticket, teacher: Teacher) -> None:
    corpo = (
        "Novo chamado aberto pelo Agente de IA de Suporte a Professores.\n\n"
        f"Professor(a): {teacher.full_name} ({teacher.username})\n"
        f"E-mail de contato: {teacher.email}\n"
        f"Escola/turma: {teacher.school or '-'} / {teacher.turma or '-'}\n\n"
        f"Pergunta original: {ticket.pergunta}\n\n"
        f"Resumo do problema: {ticket.resumo}\n\n"
        f"Chamado #{ticket.id} — aberto em {ticket.created_at:%d/%m/%Y %H:%M}"
    )
    msg = MIMEText(corpo, _charset="utf-8")
    msg["Subject"] = f"[Suporte a Professores] Chamado #{ticket.id} — {teacher.full_name}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = settings.SUPPORT_EMAIL_TO
    # Reply-To pro e-mail do professor: quem responde o e-mail de chamado já
    # fala direto com ele, sem precisar copiar/colar o endereço.
    msg["Reply-To"] = teacher.email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def abrir_chamado(db: Session, teacher: Teacher, pergunta: str, resumo: str) -> Ticket:
    ticket = Ticket(teacher_username=teacher.username, pergunta=pergunta, resumo=resumo)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    try:
        _enviar_email(ticket, teacher)
    except Exception as exc:  # nunca deixa o chamado se perder só porque o e-mail falhou
        print(f"[aviso] chamado #{ticket.id} salvo, mas o e-mail falhou: {exc}")

    return ticket
