"""RAG query service (Motor B)."""

from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.orm import Session

from itplus.app.models.query_log import QueryLog
from itplus.app.prompts.rag import RAG_SYSTEM_PROMPT
from itplus.app.schemas.chat_query import QueryResponse, SourceCitation
from itplus.app.services.llm_provider import llm_provider
from itplus.app.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)

NO_INFO_RESPONSE = "No encontré información sobre eso en la base de conocimiento."


class RAGService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.retrieval = RetrievalService(db)

    def _build_context(self, hits: list[dict]) -> str:
        parts: list[str] = []
        for i, hit in enumerate(hits, 1):
            page_info = f" (página {hit['page']})" if hit.get("page") else ""
            parts.append(
                f"[Fuente {i}: {hit['document_name']}{page_info}]\n{hit['content']}"
            )
        return "\n\n---\n\n".join(parts)

    def query(
        self,
        question: str,
        user_id: uuid.UUID | None = None,
    ) -> QueryResponse:
        start = time.perf_counter()
        hits = self.retrieval.search(question, top_k=5)

        if not hits:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._log_query(user_id, question, NO_INFO_RESPONSE, 0, latency_ms)
            return QueryResponse(answer=NO_INFO_RESPONSE, sources=[])

        context = self._build_context(hits)
        llm_messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Contexto de documentos:\n\n{context}\n\nPregunta: {question}",
            },
        ]

        try:
            answer = llm_provider.chat_completion(llm_messages, temperature=0.15)
        except Exception as exc:
            logger.error("RAG LLM call failed: %s", exc)
            answer = NO_INFO_RESPONSE

        if not answer.strip():
            answer = NO_INFO_RESPONSE

        sources = [
            SourceCitation(
                document_id=hit["document_id"],
                document_name=hit["document_name"],
                excerpt=hit["content"][:300] + ("..." if len(hit["content"]) > 300 else ""),
                page=hit.get("page"),
                score=hit["score"],
            )
            for hit in hits
        ]

        latency_ms = int((time.perf_counter() - start) * 1000)
        self._log_query(user_id, question, answer[:500], len(sources), latency_ms)

        return QueryResponse(answer=answer, sources=sources)

    def _log_query(
        self,
        user_id: uuid.UUID | None,
        question: str,
        answer_summary: str,
        sources_count: int,
        latency_ms: int,
    ) -> None:
        log = QueryLog(
            user_id=user_id,
            question=question,
            answer_summary=answer_summary,
            sources_count=sources_count,
            latency_ms=latency_ms,
            model_used=llm_provider.get_model_name(),
        )
        self.db.add(log)
        self.db.commit()

    def get_history(self, user_id: uuid.UUID | None = None, limit: int = 50) -> list[QueryLog]:
        q = self.db.query(QueryLog).order_by(QueryLog.created_at.desc())
        if user_id:
            q = q.filter(QueryLog.user_id == user_id)
        return q.limit(limit).all()
