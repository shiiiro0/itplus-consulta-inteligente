"""Celery tasks for document indexing and summary generation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from itplus.app.core.database import SessionLocal
from itplus.app.models.conversation import Conversation
from itplus.app.models.document import Document, DocumentChunk
from itplus.app.services.embedding import embedding_service
from itplus.app.services.ingestion import parse_document
from itplus.app.services.summary import SummaryService
from itplus.app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def index_document_sync(document_id: str) -> None:
    """Synchronous document indexing (fallback when Celery unavailable)."""
    db = SessionLocal()
    try:
        doc_uuid = uuid.UUID(document_id)
        document = db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            logger.error("Document %s not found", document_id)
            return

        document.status = "processing"
        db.commit()

        try:
            chunks_data = parse_document(document.storage_path, document.mime_type)
            if not chunks_data:
                raise ValueError("No se extrajo contenido del documento")

            texts = [c["content"] for c in chunks_data]
            embeddings = embedding_service.embed_texts(texts)

            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_uuid).delete()

            for idx, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
                chunk = DocumentChunk(
                    document_id=doc_uuid,
                    content=chunk_data["content"],
                    chunk_index=idx,
                    chunk_metadata={"page": chunk_data.get("page")},
                    embedding=embedding,
                )
                db.add(chunk)

            document.status = "ready"
            document.indexed_at = datetime.now(timezone.utc)
            document.error_message = None
            db.commit()
            logger.info("Document %s indexed with %d chunks", document_id, len(chunks_data))

        except Exception as exc:
            logger.error("Indexing failed for %s: %s", document_id, exc)
            document.status = "failed"
            document.error_message = str(exc)
            db.commit()
    finally:
        db.close()


@celery_app.task(name="itplus.index_document")
def index_document_task(document_id: str) -> None:
    index_document_sync(document_id)


@celery_app.task(name="itplus.generate_summary")
def generate_summary_task(conversation_id: str) -> None:
    db = SessionLocal()
    try:
        conv_uuid = uuid.UUID(conversation_id)
        conversation = db.query(Conversation).filter(Conversation.id == conv_uuid).first()
        if not conversation:
            return
        SummaryService(db).generate_summary(conv_uuid)
    finally:
        db.close()
