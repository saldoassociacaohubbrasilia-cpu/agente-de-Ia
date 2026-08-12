"""
Geração do relatório básico da turma: tenta a API do Saldo+ primeiro (se
`SALDO_API_BASE_URL` estiver configurada); se não der, usa a última
planilha carregada no sistema (ver app/routers/relatorios_router.py).

De propósito NÃO existe aqui um parser fixo pro formato exato dos dados —
nem o schema da API do Saldo+, nem o de cada planilha, são garantidos de
antemão (cada planilha pode ter colunas diferentes). Em vez disso, os dados
são resumidos (estatísticas básicas, não linha por linha) e entregues como
JSON pro próprio modelo organizar num texto legível pro professor. Isso é
mais robusto a mudança de schema do que um parser Python engessado — o
preço é confiar no bom senso do modelo pra interpretar os campos.
"""
import io
import json

import httpx
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Planilha, Teacher

settings = get_settings()

RELATORIO_SYSTEM_PROMPT = """Você resume dados de desempenho de turma pra \
um professor de educação básica. Escreva um relatório curto e direto, em \
português, com: (1) um resumo de 2-3 frases, (2) os principais números em \
bullet points, (3) um alerta se houver alunos com baixo engajamento ou sem \
acesso recente, caso essa informação exista nos dados. Baseie-se só nos \
dados fornecidos — não invente número que não esteja neles. Se os dados \
vierem sem contexto suficiente pra dizer algo útil, seja honesto sobre a \
limitação em vez de forçar uma conclusão."""

TAMANHO_MAX_UPLOAD_MB = 10


def _tentar_api_saldo(teacher: Teacher) -> dict | None:
    if not settings.SALDO_API_BASE_URL or not teacher.turma:
        return None
    try:
        resposta = httpx.get(
            f"{settings.SALDO_API_BASE_URL}/api/v1/turma/relatorio",
            params={"nome": teacher.turma},
            timeout=10.0,
        )
        resposta.raise_for_status()
        return resposta.json()
    except Exception as exc:
        print(f"[aviso] não foi possível buscar dados na API do Saldo+: {exc}")
        return None


def _resumir_planilha(db: Session, teacher: Teacher) -> dict | None:
    planilha = db.query(Planilha).order_by(desc(Planilha.created_at)).first()
    if planilha is None:
        return None

    buffer = io.BytesIO(planilha.conteudo)
    if planilha.filename.lower().endswith(".csv"):
        df = pd.read_csv(buffer)
    else:
        df = pd.read_excel(buffer)

    # tenta filtrar só a turma do professor, se existir uma coluna óbvia de turma
    coluna_turma = next(
        (c for c in df.columns if str(c).strip().lower() in ("turma", "class", "nome_turma", "classe")), None
    )
    if coluna_turma and teacher.turma:
        filtrado = df[df[coluna_turma].astype(str).str.strip().str.lower() == teacher.turma.strip().lower()]
        if not filtrado.empty:
            df = filtrado

    resumo: dict = {
        "arquivo": planilha.filename,
        "atualizado_em": planilha.created_at.isoformat(),
        "total_linhas": len(df),
        "colunas": [str(c) for c in df.columns],
    }

    numericas = df.select_dtypes(include="number")
    if not numericas.empty:
        resumo["estatisticas_numericas"] = numericas.describe().round(2).to_dict()

    categoricas = df.select_dtypes(exclude="number")
    for coluna in list(categoricas.columns)[:5]:  # limite pra não estourar o prompt com planilha muito larga
        resumo.setdefault("distribuicoes", {})[str(coluna)] = df[coluna].value_counts().head(10).to_dict()

    return resumo


def gerar_relatorio_turma(db: Session, teacher: Teacher) -> str:
    dados = _tentar_api_saldo(teacher)
    fonte = "API do Saldo+ (dado ao vivo)"
    if dados is None:
        dados = _resumir_planilha(db, teacher)
        fonte = "última planilha carregada no sistema"

    if dados is None:
        return (
            "Não encontrei dados pra gerar um relatório: a API do Saldo+ não está "
            "configurada (ou não respondeu) e ainda não existe nenhuma planilha "
            "carregada no sistema. Peça pra alguém da equipe carregar uma planilha "
            "(scripts/upload_planilha.py) ou configurar a integração com a API."
        )

    llm = ChatGoogleGenerativeAI(model=settings.GEMINI_CHAT_MODEL, google_api_key=settings.GOOGLE_API_KEY, temperature=0.2)
    mensagens = [
        ("system", RELATORIO_SYSTEM_PROMPT),
        (
            "human",
            f"Fonte dos dados: {fonte}\nTurma do professor: {teacher.turma or 'não informada'}\n\n"
            f"Dados (JSON):\n{json.dumps(dados, ensure_ascii=False, default=str)}",
        ),
    ]
    resposta = llm.invoke(mensagens)
    return resposta.content
