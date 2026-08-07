"""
Tabelas do banco de "operação" (login, chamados, planilhas).

O conteúdo pedagógico em si (PDFs) não passa por aqui — vive só no Qdrant,
na AWS. Aqui é só o que o próprio agente precisa pra funcionar no dia a dia.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160))  # pra onde a equipe responde quando abre um chamado
    school: Mapped[str | None] = mapped_column(String(120), nullable=True)
    turma: Mapped[str | None] = mapped_column(String(120), nullable=True)  # usado pra filtrar o relatório da turma
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Ticket(Base):
    """Um chamado de suporte aberto pelo agente quando a dúvida exige acompanhamento humano."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_username: Mapped[str] = mapped_column(String(80), index=True)
    pergunta: Mapped[str] = mapped_column(Text)  # a pergunta original do professor, pro contexto completo
    resumo: Mapped[str] = mapped_column(Text)  # resumo objetivo gerado pelo próprio agente
    status: Mapped[str] = mapped_column(String(20), default="aberto")  # aberto / em_andamento / resolvido
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Planilha(Base):
    """
    A última planilha carregada na base do sistema, usada pro relatório
    básico quando a API do Saldo+ não estiver configurada/disponível.
    Guarda o arquivo inteiro como bytes — pra esse volume (planilha de
    turma, não milhões de linhas) isso é mais simples do que gerenciar
    arquivo em disco, e funciona igual local e em produção.
    """

    __tablename__ = "planilhas"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    conteudo: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
