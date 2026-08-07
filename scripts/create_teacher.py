"""
CLI pra cadastrar um professor manualmente.

De propósito não existe rota de auto-cadastro público — quem decide quem
tem acesso são vocês, não é um sistema aberto. A senha é digitada
escondida (getpass), então não fica salva no histórico do terminal.

Uso:
    cd caminho/do/projeto
    python scripts/create_teacher.py --usuario maria.clara --nome "Maria Clara" --email maria@escola.com --turma "3A"
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.auth.security import get_password_hash  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Teacher  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Cadastra um novo professor no sistema de login.")
    parser.add_argument("--usuario", required=True, help="nome de usuário (login), ex: maria.clara")
    parser.add_argument("--nome", required=True, help="nome completo do professor")
    parser.add_argument("--email", required=True, help="e-mail — é pra onde a equipe responde quando abre chamado")
    parser.add_argument("--escola", default=None, help="escola (opcional)")
    parser.add_argument(
        "--turma",
        default=None,
        help="nome da turma (opcional) — usado pra filtrar o relatório básico da turma dele",
    )
    args = parser.parse_args()

    senha = getpass.getpass("Senha: ")
    confirmacao = getpass.getpass("Confirme a senha: ")
    if senha != confirmacao:
        print("As senhas não coincidem. Nada foi criado.")
        return
    if len(senha) < 6:
        print("Use uma senha com pelo menos 6 caracteres.")
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Teacher).filter(Teacher.username == args.usuario).first():
            print(f"Já existe um professor com o usuário '{args.usuario}'.")
            return
        professor = Teacher(
            username=args.usuario,
            full_name=args.nome,
            email=args.email,
            school=args.escola,
            turma=args.turma,
            hashed_password=get_password_hash(senha),
        )
        db.add(professor)
        db.commit()
        print(f"Professor '{args.nome}' cadastrado com sucesso (usuário: {args.usuario}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
