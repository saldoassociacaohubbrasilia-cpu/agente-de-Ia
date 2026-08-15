"""
Script de ingestão: lê todos os PDFs de uma pasta, quebra em pedaços, gera
embeddings e sobe pro Qdrant na AWS.

Roda LOCAL, na sua máquina — não faz parte da API que fica no ar. Execute
sempre que adicionar ou atualizar um manual pedagógico.

Uso:
    cd caminho/do/projeto
    python scripts/ingest.py --pasta ./documentos
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_community.document_loaders import PyPDFLoader  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

from app.rag.vectorstore import ensure_collection, get_embeddings, get_vectorstore  # noqa: E402

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# O tier gratuito do gemini-embedding-001 tem limite de tokens/minuto (TPM).
# Mandar tudo de uma vez estoura esse limite (erro 429); por isso a
# ingestão vai em lotes pequenos com pausa entre eles.
LOTE_TAMANHO = 20
PAUSA_ENTRE_LOTES_SEGUNDOS = 20


def carregar_pdfs(pasta: Path) -> list:
    documentos = []
    pdfs = sorted(pasta.glob("*.pdf"))
    if not pdfs:
        print(f"Nenhum PDF encontrado em {pasta}.")
        return documentos

    for pdf_path in pdfs:
        print(f"Lendo {pdf_path.name}...")
        loader = PyPDFLoader(str(pdf_path))
        paginas = loader.load()  # 1 Document por página, já com metadata["page"]
        for pagina in paginas:
            pagina.metadata["source"] = pdf_path.name  # nome curto, não o caminho inteiro
        documentos.extend(paginas)
    return documentos


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestão de PDFs no banco vetorial.")
    parser.add_argument("--pasta", default="./documentos", help="pasta com os PDFs a ingerir")
    args = parser.parse_args()

    pasta = Path(args.pasta)
    if not pasta.exists():
        print(f"Pasta '{pasta}' não existe.")
        return

    documentos = carregar_pdfs(pasta)
    if not documentos:
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    pedacos = splitter.split_documents(documentos)
    print(f"{len(documentos)} páginas -> {len(pedacos)} pedaços de texto.")

    embeddings = get_embeddings()
    vector_size = len(embeddings.embed_query("teste de dimensão do vetor"))
    ensure_collection(vector_size)

    vectorstore = get_vectorstore()
    total_lotes = (len(pedacos) + LOTE_TAMANHO - 1) // LOTE_TAMANHO
    for i in range(0, len(pedacos), LOTE_TAMANHO):
        lote = pedacos[i : i + LOTE_TAMANHO]
        numero_lote = i // LOTE_TAMANHO + 1
        print(f"Indexando lote {numero_lote}/{total_lotes} ({len(lote)} pedaços)...")
        vectorstore.add_documents(lote)
        if numero_lote < total_lotes:
            time.sleep(PAUSA_ENTRE_LOTES_SEGUNDOS)
    print(f"Pronto! {len(pedacos)} pedaços indexados na coleção '{vectorstore.collection_name}' do Qdrant.")


if __name__ == "__main__":
    main()
