"""
Configurações centrais da aplicação.

Tudo que muda entre "rodando no seu PC" e "rodando em produção" mora aqui,
lido a partir de variáveis de ambiente (.env). Nunca hardcode uma chave de
API no código — é assim que ela vaza pro GitHub sem querer.
"""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("*", mode="before")
    @classmethod
    def _strip_strings(cls, v):
        # Campos colados manualmente no painel do Render (ou outro provedor)
        # às vezes carregam uma quebra de linha ou espaço invisível no final
        # — o suficiente pra virar "postgres\n" em vez de "postgres" e
        # quebrar a conexão. Tira isso de toda variável de ambiente lida.
        return v.strip() if isinstance(v, str) else v

    # --- Autenticação ---
    SECRET_KEY: str  # gere com: python -c "import secrets; print(secrets.token_hex(32))"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8h — dura um dia de trabalho do professor

    # --- Banco de dados de login (professores) ---
    # Não tem nada a ver com o banco vetorial — esse aqui só guarda usuário/senha.
    DATABASE_URL: str = "sqlite:///./teachers.db"

    # --- Banco vetorial (Qdrant rodando numa EC2 free tier na AWS) ---
    QDRANT_URL: str  # ex: http://SEU_IP_PUBLICO_EC2:6333
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str = "materiais_pedagogicos"

    # --- Google Gemini (chat + embeddings — provedor único, por escolha sua) ---
    GOOGLE_API_KEY: str
    # "gemini-flash-latest" é um alias mantido pelo Google que sempre aponta
    # pro modelo flash atual (tier gratuito, suporta tool calling — usado
    # pra abrir chamado e gerar relatório). Usar o alias em vez de fixar uma
    # versão evita quebrar quando o Google descontinua um modelo específico
    # (já aconteceu com gemini-2.0-flash e gemini-2.5-flash neste projeto).
    # Pra produção, se quiser mais previsibilidade, fixe uma versão
    # conferindo antes em ai.google.dev/gemini-api/docs/models.
    GEMINI_CHAT_MODEL: str = "gemini-flash-latest"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"

    # --- CORS: de onde o frontend (ex: GitHub Pages) pode chamar a API ---
    CORS_ORIGINS: str = "http://localhost:5500"  # separe por vírgula se tiver mais de uma origem

    # --- E-mail (abertura de chamado) ---
    # Qualquer provedor SMTP serve — Gmail com "senha de app", Outlook, etc.
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: str
    SUPPORT_EMAIL_TO: str  # pra onde vai o e-mail de chamado aberto (ex: suporte@seuprograma.org)

    # --- Relatório da turma ---
    # Opcional: URL base do backend do Saldo+, se quiser que o relatório
    # busque dados ao vivo da API em vez de depender só de planilha
    # carregada manualmente. Ex: https://saldo-backend.onrender.com
    SALDO_API_BASE_URL: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
