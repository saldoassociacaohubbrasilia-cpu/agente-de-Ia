"""
Tabelas do banco de "operação" (login, chamados, planilhas).

O conteúdo pedagógico em si (PDFs) não passa por aqui — vive só no Qdrant,
na AWS. Aqui é só o que o próprio agente precisa pra funcionar no dia a dia.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class Conversa(Base):
    """Uma conversa do professor com o agente — agrupa as mensagens trocadas, pro histórico da lateral."""

    __tablename__ = "conversas"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_username: Mapped[str] = mapped_column(String(80), index=True)
    # título curto pra listar na lateral — gerado a partir da primeira pergunta, não editável por enquanto
    titulo: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    mensagens: Mapped[list["Mensagem"]] = relationship(
        back_populates="conversa", order_by="Mensagem.created_at", cascade="all, delete-orphan"
    )


class Mensagem(Base):
    """Uma mensagem dentro de uma conversa — do professor ou do agente."""

    __tablename__ = "mensagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversa_id: Mapped[int] = mapped_column(ForeignKey("conversas.id"), index=True)
    autor: Mapped[str] = mapped_column(String(20))  # "professor" ou "agente"
    texto: Mapped[str] = mapped_column(Text)
    # só preenchido em mensagens do agente — lista de {"arquivo": ..., "pagina": ...}
    fontes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    chamado_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversa: Mapped["Conversa"] = relationship(back_populates="mensagens")


class PasswordResetToken(Base):
    """Token de uso único pra redefinir senha — expira rápido e é apagado assim que usado (ou quando expira)."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_username: Mapped[str] = mapped_column(String(80), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
