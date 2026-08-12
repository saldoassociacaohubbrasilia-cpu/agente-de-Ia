"""Teste rápido: confirma se a chave do Gemini (lida do .env) funciona."""
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_settings

settings = get_settings()
client = ChatGoogleGenerativeAI(model=settings.GEMINI_CHAT_MODEL, google_api_key=settings.GOOGLE_API_KEY)

resposta = client.invoke("Escreva um haicai sobre educação.")
print(resposta.content)
