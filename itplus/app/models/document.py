import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from itplus.app.core.config import get_settings
from itplus.app.core.database import Base

_settings = get_settings()


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(1000), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    source_type = Column(String(50), nullable=False, default="upload")
    category = Column(String(50), nullable=False, default="general")
    description = Column(Text, nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    analyst_profile = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    indexed_at = Column(DateTime(timezone=True), nullable=True)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_metadata = Column("metadata", JSONB, nullable=True, default=dict)
    embedding = Column(Vector(_settings.embedding_dimensions), nullable=True)

    document = relationship("Document", back_populates="chunks")
