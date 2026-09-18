"""Document upload and management endpoints."""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_user
from itplus.app.core.config import get_settings
from itplus.app.core.database import get_db
from itplus.app.models.document import Document
from itplus.app.models.user import User
from itplus.app.schemas.documents import DocumentResponse

from itplus.app.core.phases import KNOWLEDGE_CATEGORIES

router = APIRouter()

ALLOWED_CATEGORIES = {c["key"] for c in KNOWLEDGE_CATEGORIES}

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.ms-excel.sheet.macroEnabled.12",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/csv",
}

# Muchos navegadores/clientes HTTP mandan un content-type genérico (o vacío)
# en vez del real. No lo rechazamos —igual la extensión ya se validó arriba—
# pero sí rechazamos un content-type reconocido que no coincide con ninguno
# de los permitidos (p. ej. subir un .exe renombrado a .pdf con
# "application/x-msdownload").
GENERIC_CONTENT_TYPES = {"application/octet-stream", ""}

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".xlsm"}


def _queue_indexing(document_id: uuid.UUID) -> None:
    try:
        from itplus.app.workers.index_document import index_document_task

        index_document_task.delay(str(document_id))
    except Exception:
        from itplus.app.workers.index_document import index_document_sync

        index_document_sync(str(document_id))


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    description: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo requerido")

    # Solo nos importa la extensión del nombre original para validarla; el
    # nombre en sí nunca se usa para construir la ruta en disco (ver abajo),
    # así que un ".." o "/" en file.filename no puede escapar de upload_dir.
    original_name = Path(file.filename).name
    suffix = Path(original_name).suffix.lower()
    if not original_name or suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado. Usa: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Archivo excede el límite de {settings.max_upload_mb} MB",
        )

    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in ALLOWED_TYPES and mime_type not in GENERIC_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de contenido no permitido: {mime_type}",
        )

    doc_id = uuid.uuid4()
    # El nombre en disco se deriva únicamente del UUID que generamos y de una
    # extensión ya validada contra ALLOWED_EXTENSIONS — nunca del nombre que
    # manda el cliente — para eliminar cualquier posibilidad de path traversal.
    safe_name = f"{doc_id}{suffix}"
    storage_path = (upload_dir / safe_name).resolve()
    if storage_path.parent != upload_dir.resolve():
        # Defensa en profundidad: no debería poder pasar, pero si pasa, cortamos.
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")

    with open(storage_path, "wb") as f:
        f.write(content)

    cat = (category or "general").strip().lower()
    if cat not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Categoría inválida. Usa: {', '.join(sorted(ALLOWED_CATEGORIES))}")

    document = Document(
        id=doc_id,
        filename=original_name,
        mime_type=mime_type,
        storage_path=str(storage_path),
        status="pending",
        source_type="upload",
        category=cat,
        description=(description or "").strip() or None,
        uploaded_by=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    _queue_indexing(document.id)

    return document


@router.get("/categories")
def list_categories(current_user: User = Depends(get_current_user)):
    return {"categories": KNOWLEDGE_CATEGORIES}


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return docs


@router.post("/{document_id}/reindex", response_model=DocumentResponse)
def reindex_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    document.status = "pending"
    document.error_message = None
    db.commit()
    db.refresh(document)

    _queue_indexing(document.id)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    settings = get_settings()
    upload_dir = Path(settings.upload_dir).resolve()
    storage = Path(document.storage_path).resolve()
    if storage.parent == upload_dir and storage.exists():
        storage.unlink()

    db.delete(document)
    db.commit()
