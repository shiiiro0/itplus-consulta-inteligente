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
    "text/plain",
    "text/markdown",
    "text/csv",
}

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

    suffix = Path(file.filename).suffix.lower()
    if suffix and suffix not in ALLOWED_EXTENSIONS:
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
    doc_id = uuid.uuid4()
    safe_name = f"{doc_id}_{file.filename}"
    storage_path = upload_dir / safe_name

    with open(storage_path, "wb") as f:
        f.write(content)

    cat = (category or "general").strip().lower()
    if cat not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Categoría inválida. Usa: {', '.join(sorted(ALLOWED_CATEGORIES))}")

    document = Document(
        id=doc_id,
        filename=file.filename,
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

    storage = Path(document.storage_path)
    if storage.exists():
        storage.unlink()

    db.delete(document)
    db.commit()
