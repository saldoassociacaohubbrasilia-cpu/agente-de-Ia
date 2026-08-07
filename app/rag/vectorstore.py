"""
Conexão com o Qdrant hospedado na EC2 (ver infra/ec2_user_data.sh).

Por que Qdrant e não Chroma: a autenticação por API key no Qdrant é uma
única variável de ambiente no servidor (QDRANT__SERVICE__API_KEY) — sem
precisar configurar um "auth provider" à parte. Como aqui é uma instância
que só você vai administrar, isso pesou bastante na escolha.
"""
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.config import get_settings

settings = get_settings()


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    # A Anthropic não tem endpoint próprio de embeddings — pra isso, a
    # própria Anthropic recomenda a Voyage AI. Usamos OpenAI aqui por ser
    # simples e barata; pra trocar por Voyage, troca só essa função (usar
    # `langchain_voyageai.VoyageAIEmbeddings`) — o resto do pipeline
    # (Qdrant, chain, ingestão) não muda nada, porque todos trabalham só
    # com a interface genérica `Embeddings` do LangChain.
    return OpenAIEmbeddings(model=settings.EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY)


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
