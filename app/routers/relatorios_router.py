"""
Upload da planilha que alimenta o relatório básico quando a API do Saldo+
não estiver configurada/disponível (ver app/rag/relatorios.py).

Fica guardada no banco (não em disco) — funciona igual local e em produção,
e não depende do disco do Render (que não é persistente entre deploys).
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.security import get_current_teacher
from app.database import get_db
from app.models import Planilha, Teacher

router = APIRouter(tags=["relatórios"])

EXTENSOES_PERMITIDAS = (".xlsx", ".csv")
TAMANHO_MAX_BYTES = 10 * 1024 * 1024  # 10MB — de sobra pra planilha de turma, evita abuso


@router.post("/planilhas")
async def upload_planilha(
    arquivo: UploadFile = File(...),
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
) -> dict:
    if not arquivo.filename.lower().endswith(EXTENSOES_PERMITIDAS):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx ou .csv")

    conteudo = await arquivo.read()
    if len(conteudo) > TAMANHO_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo maior que 10MB")

    planilha = Planilha(filename=arquivo.filename, conteudo=conteudo, uploaded_by=current_teacher.username)
    db.add(planilha)
    db.commit()
    db.refresh(planilha)
    return {"mensagem": f"Planilha '{arquivo.filename}' recebida e será usada nos próximos relatórios.", "id": planilha.id}
