"""Document knowledge base connector (Phase 1 — active)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from itplus.app.connectors.base import (
    BaseConnector,
    ConnectorHit,
    ConnectorPhase,
    ConnectorResult,
    ConnectorStatus,
    QueryContext,
)
from itplus.app.services.document_analytics import resolve_retrieval_question, wants_analytics
from itplus.app.services.retrieval import RetrievalService


class DocumentConnector(BaseConnector):
    key = "documents"
    label = "Base de conocimiento (documentos)"
    phase = ConnectorPhase.ACTIVE
    description = (
        "Consulta información indexada desde PDF, DOCX, TXT y CSV subidos a la plataforma."
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self._retrieval = RetrievalService(db)

    def is_available(self) -> bool:
        from itplus.app.models.document import Document

        return (
            self.db.query(Document).filter(Document.status == "ready").limit(1).first()
            is not None
        )

    def query(self, ctx: QueryContext) -> ConnectorResult:
        query_text = resolve_retrieval_question(ctx.question, ctx.conversation_history)
        if wants_analytics(query_text):
            hits = self._retrieval.search_for_analytics(
                query_text,
                category=ctx.category,
            )
        else:
            hits = self._retrieval.search(
                query_text,
                top_k=6,
                min_score=0.28,
                category=ctx.category,
            )
        if not hits:
            return ConnectorResult(
                connector_key=self.key,
                connector_label=self.label,
                status=ConnectorStatus.READY,
                hits=[],
                message="No se encontraron fragmentos relevantes en los documentos.",
            )

        connector_hits = [
            ConnectorHit(
                source_id=str(h["document_id"]),
                source_name=h["document_name"],
                content=h["content"],
                score=h["score"],
                metadata={"page": h.get("page"), "chunk_id": str(h["chunk_id"])},
            )
            for h in hits
        ]
        return ConnectorResult(
            connector_key=self.key,
            connector_label=self.label,
            status=ConnectorStatus.READY,
            hits=connector_hits,
        )
