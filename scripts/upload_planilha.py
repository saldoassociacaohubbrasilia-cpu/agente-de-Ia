"""
Envia uma planilha (.xlsx ou .csv) pra base do sistema — ela passa a ser a
"última planilha carregada", usada pro relatório básico quando a API do
Saldo+ não estiver configurada/disponível.

Uso:
    cd caminho/do/projeto
    python scripts/upload_planilha.py --arquivo ./relatorio_turmas.xlsx --usuario maria.clara
"""
import argparse
import getpass
import sys
from pathlib import Path

import httpx

sys.path.append(str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Envia uma planilha pra base do sistema.")
    parser.add_argument("--arquivo", required=True, help="caminho do .xlsx ou .csv")
    parser.add_argument("--usuario", required=True, help="seu usuário de login")
    parser.add_argument("--api-base", default="http://localhost:8000/api/v1", help="URL base da API")
    args = parser.parse_args()

    caminho = Path(args.arquivo)
    if not caminho.exists():
        print(f"Arquivo '{caminho}' não encontrado.")
        return
    if caminho.suffix.lower() not in (".xlsx", ".csv"):
        print("Envie um arquivo .xlsx ou .csv.")
        return

    senha = getpass.getpass("Senha: ")

    login = httpx.post(f"{args.api_base}/login", data={"username": args.usuario, "password": senha})
    if login.status_code != 200:
        print(f"Login falhou: {login.text}")
        return
    token = login.json()["access_token"]

    with open(caminho, "rb") as f:
        resposta = httpx.post(
            f"{args.api_base}/planilhas",
            headers={"Authorization": f"Bearer {token}"},
            files={"arquivo": (caminho.name, f)},
            timeout=30.0,
        )

    if resposta.status_code == 200:
        print(resposta.json()["mensagem"])
    else:
        print(f"Falha ao enviar: {resposta.text}")


if __name__ == "__main__":
    main()
