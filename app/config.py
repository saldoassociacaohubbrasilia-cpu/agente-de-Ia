"""
Configurações centrais da aplicação.

Tudo que muda entre "rodando no seu PC" e "rodando em produção" mora aqui,
lido a partir de variáveis de ambiente (.env). Nunca hardcode uma chave de
API no código — é assim que ela vaza pro GitHub sem querer.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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

    # --- LLM (Claude, via Anthropic) ---
    ANTHROPIC_API_KEY: str
    # Haiku é o modelo mais em conta da família Claude — bom ponto de partida
    # pro custo de um agente que vai responder muita pergunta repetida do
    # dia a dia. Se quiser respostas mais elaboradas, troque por claude-sonnet-5.
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"

    # --- Embeddings (texto -> vetor, usado na ingestão e em toda pergunta) ---
    # A Anthropic não tem endpoint próprio de embeddings; usamos a OpenAI aqui
    # por ser simples e barata. (A própria Anthropic recomenda a Voyage AI
    # como alternativa — dá pra trocar sem mexer no resto do pipeline.)
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"

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
