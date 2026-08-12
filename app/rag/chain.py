"""
A cadeia de RAG + ferramentas.

Fluxo: pergunta -> busca no Qdrant -> Gemini decide, com base no contexto e
no system prompt, se (a) responde direto usando os trechos recuperados,
(b) chama a ferramenta de abrir chamado, porque é um problema real que
precisa de acompanhamento humano, ou (c) chama a ferramenta de gerar
relatório, porque o professor pediu um resumo de desempenho da turma.

Fica separado do router (app/routers/chat_router.py) de propósito: assim dá
pra testar essa lógica sozinha, e o router consegue trocar essa função por
um "dublê" nos testes (ver tests/test_auth.py e tests/test_ferramentas.py).
"""
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Teacher
from app.rag.prompts import SYSTEM_PROMPT
from app.rag.relatorios import gerar_relatorio_turma
from app.rag.vectorstore import get_vectorstore
from app.support.tickets import abrir_chamado

settings = get_settings()

TOP_K = 4  # quantos trechos de documento buscar por pergunta
MAX_RODADAS_DE_FERRAMENTA = 3  # trava de segurança: nunca deixa entrar num loop de chamada de ferramenta


def _format_context(docs: list[Document]) -> str:
    if not docs:
        return "(nenhum trecho relevante encontrado na base de materiais)"
    blocos = []
    for i, doc in enumerate(docs, start=1):
        fonte = doc.metadata.get("source", "documento desconhecido")
        pagina = doc.metadata.get("page")
        cabecalho = f"[Trecho {i} — {fonte}" + (f", página {pagina}" if pagina is not None else "") + "]"
        blocos.append(f"{cabecalho}\n{doc.page_content}")
    return "\n\n".join(blocos)


def _format_fontes(docs: list[Document]) -> list[dict]:
    vistas: set[tuple] = set()
    fontes = []
    for doc in docs:
        chave = (doc.metadata.get("source"), doc.metadata.get("page"))
        if chave in vistas:
            continue
        vistas.add(chave)
        fontes.append({"arquivo": doc.metadata.get("source", "desconhecido"), "pagina": doc.metadata.get("page")})
    return fontes


def answer_question(question: str, teacher: Teacher, db: Session) -> dict:
    """Ponto de entrada usado pelo router de /chat."""
    vectorstore = get_vectorstore()
    docs = vectorstore.similarity_search(question, k=TOP_K)
    contexto = _format_context(docs)

    chamados_abertos: list[int] = []

    # As duas ferramentas ficam definidas AQUI DENTRO (não no módulo) porque
    # precisam "lembrar" o professor logado e a sessão de banco da request
    # atual — um fechamento (closure) simples resolve isso sem precisar de
    # injeção de dependência mais complexa dentro da própria tool.
    @tool
    def abrir_chamado_de_suporte(resumo: str) -> str:
        """Abre um chamado de suporte humano para a equipe entrar em contato
        com o professor por e-mail. Use SOMENTE quando o professor relatar um
        problema real que precisa de acompanhamento de alguém da equipe (ex:
        problema de acesso/login, erro no sistema, reclamação, pedido de
        suporte que não é uma dúvida de conteúdo). NÃO use só porque a
        resposta não estava nos materiais pedagógicos — nesse caso, oriente
        o professor a consultar a coordenação, sem abrir chamado. `resumo`
        deve ser uma frase objetiva descrevendo o problema, pra equipe
        entender rápido do que se trata antes de entrar em contato."""
        ticket = abrir_chamado(db, teacher, question, resumo)
        chamados_abertos.append(ticket.id)
        return f"Chamado #{ticket.id} registrado. A equipe vai entrar em contato pelo e-mail {teacher.email}."

    @tool
    def gerar_relatorio() -> str:
        """Gera um relatório básico da turma do professor logado (progresso,
        engajamento, alunos sem acesso recente etc.), usando a API do Saldo+
        se estiver configurada ou a última planilha carregada no sistema
        como alternativa. Use quando o professor pedir um relatório, resumo
        de desempenho, ou "como está minha turma"."""
        return gerar_relatorio_turma(db, teacher)

    ferramentas = {"abrir_chamado_de_suporte": abrir_chamado_de_suporte, "gerar_relatorio": gerar_relatorio}

    llm = ChatGoogleGenerativeAI(model=settings.GEMINI_CHAT_MODEL, google_api_key=settings.GOOGLE_API_KEY, temperature=0.2)
    llm_com_ferramentas = llm.bind_tools(list(ferramentas.values()))

    mensagens = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=f"Contexto (trechos dos materiais pedagógicos):\n\n{contexto}\n\nPergunta do professor: {question}"
        ),
    ]

    for _ in range(MAX_RODADAS_DE_FERRAMENTA):
        resposta = llm_com_ferramentas.invoke(mensagens)

        if not resposta.tool_calls:
            return {
                "resposta": resposta.content,
                "fontes": _format_fontes(docs),
                "chamado_id": chamados_abertos[0] if chamados_abertos else None,
            }

        mensagens.append(resposta)
        for chamada in resposta.tool_calls:
            resultado = ferramentas[chamada["name"]].invoke(chamada["args"])
            mensagens.append(ToolMessage(content=str(resultado), tool_call_id=chamada["id"]))

    # estourou o limite de rodadas sem chegar numa resposta final em texto —
    # não deveria acontecer, mas se acontecer, força uma resposta final.
    resposta_final = llm.invoke(mensagens)
    return {
        "resposta": resposta_final.content,
        "fontes": _format_fontes(docs),
        "chamado_id": chamados_abertos[0] if chamados_abertos else None,
    }
