"""Document upload and management endpoints."""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_user
from itplus.app.core.config import get_settings
from itplus.app.core.database import get_db
from itplus.app.models.document import Document
from itplus.app.models.user import User
from itplus.app.schemas.documents import DocumentResponse

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/csv",
}


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo requerido")

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

    document = Document(
        id=doc_id,
        filename=file.filename,
        mime_type=mime_type,
        storage_path=str(storage_path),
        status="pending",
        uploaded_by=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        from itplus.app.workers.index_document import index_document_task

        index_document_task.delay(str(document.id))
    except Exception:
        from itplus.app.workers.index_document import index_document_sync

        index_document_sync(str(document.id))

    return document


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return docs


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
