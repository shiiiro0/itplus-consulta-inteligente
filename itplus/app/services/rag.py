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
from itplus.app.utils.document_location import format_document_location, parse_document_location
from itplus.app.utils.small_talk import is_small_talk

logger = logging.getLogger(__name__)

NO_INFO_RESPONSE = "No encontré información sobre eso en la base de conocimiento."


class RAGService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.retrieval = RetrievalService(db)

    def _build_context(self, hits: list[dict]) -> str:
        parts: list[str] = []
        for i, hit in enumerate(hits, 1):
            page, sheet = parse_document_location(hit)
            loc = format_document_location(page, sheet)
            parts.append(
                f"[Fuente {i}: {hit['document_name']}{loc}]\n{hit['content']}"
            )
        return "\n\n---\n\n".join(parts)

    def query(
        self,
        question: str,
        user_id: uuid.UUID | None = None,
        category: str | None = None,
    ) -> QueryResponse:
        start = time.perf_counter()
        resolved = (category or "general").strip().lower()
        hits = self.retrieval.search_multi(
            question,
            categories=[resolved],
            top_k=5,
        )

        if not hits:
            if is_small_talk(question):
                llm_messages = [
                    {"role": "system", "content": RAG_SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ]
                try:
                    answer = llm_provider.chat_completion(llm_messages, temperature=0.3)
                except Exception as exc:
                    logger.error("RAG greeting LLM call failed: %s", exc)
                    answer = (
                        "¡Hola! Soy tu consultor documental de ITPlus. "
                        "Pregúntame sobre políticas, procedimientos o documentos que hayas cargado."
                    )
                latency_ms = int((time.perf_counter() - start) * 1000)
                log = self._log_query(user_id, question, answer[:500], 0, latency_ms)
                return QueryResponse(answer=answer, sources=[], id=log.id)

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

        sources = []
        for hit in hits:
            page, sheet = parse_document_location(hit)
            sources.append(
                SourceCitation(
                    document_id=hit["document_id"],
                    document_name=hit["document_name"],
                    excerpt=hit["content"][:300] + ("..." if len(hit["content"]) > 300 else ""),
                    page=page,
                    sheet=sheet,
                    score=hit["score"],
                )
            )

        latency_ms = int((time.perf_counter() - start) * 1000)
        log = self._log_query(user_id, question, answer[:500], len(sources), latency_ms)

        return QueryResponse(answer=answer, sources=sources, id=log.id)

    def _log_query(
        self,
        user_id: uuid.UUID | None,
        question: str,
        answer_summary: str,
        sources_count: int,
        latency_ms: int,
    ) -> QueryLog:
        log = QueryLog(
            user_id=user_id,
            question=question,
            answer_summary=answer_summary,
            sources_count=sources_count,
            latency_ms=latency_ms,
            model_used=llm_provider.get_model_name(),
            chat_type="consulta",
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_history(self, user_id: uuid.UUID | None = None, limit: int = 50) -> list[QueryLog]:
        from sqlalchemy import or_

        q = (
            self.db.query(QueryLog)
            .filter(or_(QueryLog.chat_type == "consulta", QueryLog.chat_type.is_(None)))
            .order_by(QueryLog.created_at.desc())
        )
        if user_id:
            q = q.filter(QueryLog.user_id == user_id)
        return q.limit(limit).all()
