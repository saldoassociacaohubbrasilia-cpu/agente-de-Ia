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
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_community.document_loaders import PyPDFLoader  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

from app.rag.vectorstore import ensure_collection, get_embeddings, get_vectorstore  # noqa: E402

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


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
    vectorstore.add_documents(pedacos)
    print(f"Pronto! {len(pedacos)} pedaços indexados na coleção '{vectorstore.collection_name}' do Qdrant.")


if __name__ == "__main__":
    main()
