"""
Conexão com o Qdrant hospedado na EC2 (ver infra/ec2_user_data.sh).

Por que Qdrant e não Chroma: a autenticação por API key no Qdrant é uma
única variável de ambiente no servidor (QDRANT__SERVICE__API_KEY) — sem
precisar configurar um "auth provider" à parte. Como aqui é uma instância
que só você vai administrar, isso pesou bastante na escolha.
"""
from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.config import get_settings

settings = get_settings()


@lru_cache
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    # Mesmo provedor do chat (Gemini), só que fazendo texto -> vetor — não
    # conversa com ninguém. Usado na ingestão dos PDFs e a cada pergunta,
    # pra achar os trechos mais parecidos antes de montar o prompt.
    return GoogleGenerativeAIEmbeddings(model=settings.GEMINI_EMBEDDING_MODEL, google_api_key=settings.GOOGLE_API_KEY)


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


def ensure_collection(vector_size: int) -> None:
    """Cria a coleção no Qdrant se ela ainda não existir. Chamado pelo script de ingestão."""
    client = get_qdrant_client()
    existentes = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION_NAME not in existentes:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


@lru_cache
def get_vectorstore() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=get_qdrant_client(),
        collection_name=settings.QDRANT_COLLECTION_NAME,
        embedding=get_embeddings(),
    )
