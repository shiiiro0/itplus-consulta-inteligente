"""Managerial assistant — unified conversational query over connectors."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from itplus.app.connectors.base import ConnectorHit, ConnectorResult, QueryContext
from itplus.app.connectors.registry import query_all
from itplus.app.models.conversation import Conversation, Message
from itplus.app.prompts.assistant import ASSISTANT_SYSTEM_PROMPT, NO_CONTEXT_RESPONSE
from itplus.app.schemas.analytics import AnalyticsPayload
from itplus.app.schemas.assistant import AssistantSource, ConnectorInfo
from itplus.app.services.document_analytics import build_analytics, build_analytics_context, resolve_retrieval_question, wants_analytics, _format_clp_short
from itplus.app.services.crisp_analyst import run_crisp_pipeline
from itplus.app.services.llm_provider import llm_provider
from itplus.app.utils.document_location import format_document_location, parse_document_location

logger = logging.getLogger(__name__)

ASSISTANT_CONTEXT_TYPE = "assistant"


def _title_from_message(text: str, max_len: int = 80) -> str:
    t = (text or "").strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


@dataclass
class PreparedAssistantTurn:
    conversation: Conversation
    llm_messages: list[dict[str, str]] | None
    hits: list[ConnectorHit]
    connectors_used: list[ConnectorInfo]
    sources: list[AssistantSource]
    no_context: bool
    static_answer: str | None = None
    analytics: AnalyticsPayload | None = None
    crisp_steps: list[dict[str, str]] | None = None


class AssistantService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _build_analytics_fallback_answer(self, analytics: AnalyticsPayload | None) -> str | None:
        if not analytics:
            return None
        if not analytics.charts and not analytics.tables and not analytics.comparisons:
            return None

        parts: list[str] = []
        if analytics.comparisons:
            comparison = analytics.comparisons[0]
            direction = "subieron" if comparison.change_pct >= 0 else "bajaron"
            trend = "favorable" if comparison.change_pct >= 0 else "a revisar"
            if comparison.unit == "clp" and comparison.value_a > 0 and comparison.value_b > 0:
                parts.append(
                    f"En {comparison.label.lower()}, las ventas {direction} un {abs(comparison.change_pct):.1f}% "
                    f"respecto a {comparison.period_a}: de {_format_clp_short(comparison.value_a)} "
                    f"a {_format_clp_short(comparison.value_b)} en {comparison.period_b}."
                )
            else:
                parts.append(
                    f"{comparison.label}: {direction} {abs(comparison.change_pct):.1f}% "
                    f"de {comparison.period_a} a {comparison.period_b}."
                )
            parts.append(
                f"La tendencia es {trend} para el trimestre. Conviene revisar qué meses concentraron "
                "el movimiento antes de ajustar metas o acciones comerciales."
            )
        else:
            parts.append("Con los datos disponibles, el análisis quedó listo para revisión.")
        if analytics.charts or analytics.tables:
            parts.append("Si quieres, te muestro el desglose en gráficos de torta y tablas.")
        return "\n\n".join(parts)

    def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.context_type == ASSISTANT_CONTEXT_TYPE,
            )
            .first()
        )

    def create_conversation(self, user_id: uuid.UUID | None = None) -> Conversation:
        if user_id:
            self._close_other_active_sessions(user_id)
        conversation = Conversation(
            user_id=user_id,
            context_type=ASSISTANT_CONTEXT_TYPE,
            status="active",
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_active_conversation(self, user_id: uuid.UUID) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .filter(
                Conversation.user_id == user_id,
                Conversation.context_type == ASSISTANT_CONTEXT_TYPE,
                Conversation.status == "active",
            )
            .order_by(Conversation.created_at.desc())
            .first()
        )

    def close_conversation(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        conversation = self.get_conversation(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ValueError("Conversación no encontrada")
        if conversation.status == "finished":
            return
        conversation.status = "finished"
        conversation.finished_at = datetime.now(timezone.utc)
        self.db.commit()

    def _close_other_active_sessions(self, user_id: uuid.UUID, keep_id: uuid.UUID | None = None) -> None:
        actives = (
            self.db.query(Conversation)
            .filter(
                Conversation.user_id == user_id,
                Conversation.context_type == ASSISTANT_CONTEXT_TYPE,
                Conversation.status == "active",
            )
            .all()
        )
        now = datetime.now(timezone.utc)
        changed = False
        for conv in actives:
            if keep_id and conv.id == keep_id:
                continue
            conv.status = "finished"
            conv.finished_at = now
            changed = True
        if changed:
            self.db.commit()

    def get_messages(self, conversation_id: uuid.UUID) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

    def _build_history(self, messages: list[Message]) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        for msg in messages:
            if msg.role in ("user", "assistant"):
                history.append({"role": msg.role, "content": msg.content})
        return history[-12:]

    def _build_context_block(self, results: list[ConnectorResult]) -> tuple[str, list[ConnectorHit]]:
        all_hits: list[ConnectorHit] = []
        sections: list[str] = []

        for result in results:
            if not result.hits:
                continue
            for i, hit in enumerate(result.hits, 1):
                all_hits.append(hit)
                page, sheet = parse_document_location(hit.metadata)
                loc = format_document_location(page, sheet)
                sections.append(f"[{i}] Documento: {hit.source_name}{loc}\n{hit.content}")

        return "\n\n".join(sections), all_hits

    def _hits_to_sources(self, hits: list[ConnectorHit]) -> list[AssistantSource]:
        seen_docs: set[str] = set()
        sources: list[AssistantSource] = []
        for hit in hits:
            if hit.source_id in seen_docs:
                continue
            seen_docs.add(hit.source_id)
            page, sheet = parse_document_location(hit.metadata)
            sources.append(
                AssistantSource(
                    source_id=hit.source_id,
                    source_name=hit.source_name,
                    excerpt="",
                    page=page,
                    sheet=sheet,
                    score=hit.score,
                    connector_key=hit.metadata.get("connector_key", "documents"),
                )
            )
        return sources

    def _prepare_turn(
        self,
        message: str,
        conversation_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        category: str | None,
    ) -> PreparedAssistantTurn:
        if conversation_id:
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError("Conversación no encontrada")
        else:
            conversation = self.create_conversation(user_id)

        user_msg = Message(conversation_id=conversation.id, role="user", content=message)
        self.db.add(user_msg)
        if not conversation.title:
            conversation.title = _title_from_message(message)
        self.db.flush()

        prior_messages = self.get_messages(conversation.id)
        history = self._build_history(prior_messages)
        retrieval_question = resolve_retrieval_question(message, history)

        ctx = QueryContext(
            question=retrieval_question,
            category=category,
            conversation_history=history,
            user_id=str(user_id) if user_id else None,
        )
        connector_results = query_all(self.db, ctx)

        for result in connector_results:
            for hit in result.hits:
                hit.metadata["connector_key"] = result.connector_key

        context_block, hits = self._build_context_block(connector_results)

        crisp_steps: list[dict[str, str]] | None = None
        crisp_context: str | None = None
        analytics: AnalyticsPayload | None = None
        if wants_analytics(retrieval_question):
            crisp_result = run_crisp_pipeline(
                self.db,
                message,
                category,
                history,
            )
            if crisp_result.steps:
                crisp_steps = [
                    {"phase": s.phase, "label": s.label, "detail": s.detail}
                    for s in crisp_result.steps
                ]
            if crisp_result.success:
                crisp_context = crisp_result.llm_context
                if crisp_result.analytics:
                    analytics = crisp_result.analytics
                else:
                    analytics = build_analytics(hits, retrieval_question)
            else:
                analytics = build_analytics(hits, retrieval_question)
        else:
            analytics = build_analytics(hits, retrieval_question)

        tabular_summary = build_analytics_context(analytics, hits, retrieval_question)
        if crisp_context:
            tabular_summary = (
                f"{crisp_context}\n\n{tabular_summary}" if tabular_summary else crisp_context
            )
        connectors_used = [
            ConnectorInfo(
                key=r.connector_key,
                label=r.connector_label,
                status=r.status.value,
                hits_count=len(r.hits),
                message=r.message,
            )
            for r in connector_results
        ]
        sources = self._hits_to_sources(hits)

        if not hits and not crisp_context:
            return PreparedAssistantTurn(
                conversation=conversation,
                llm_messages=None,
                hits=hits,
                connectors_used=connectors_used,
                sources=sources,
                no_context=True,
                static_answer=NO_CONTEXT_RESPONSE,
                crisp_steps=crisp_steps,
            )

        context_parts = []
        if tabular_summary:
            context_parts.append(tabular_summary)
        if context_block:
            context_parts.append(context_block)
        full_context = "\n\n".join(context_parts)

        llm_messages: list[dict[str, str]] = [{"role": "system", "content": ASSISTANT_SYSTEM_PROMPT}]
        for turn in history[:-1]:
            llm_messages.append(turn)
        llm_messages.append(
            {
                "role": "user",
                "content": (
                    f"Datos de los reportes:\n\n{full_context}\n\n"
                    f"Pregunta del gerente: {message}"
                ),
            }
        )

        return PreparedAssistantTurn(
            conversation=conversation,
            llm_messages=llm_messages,
            hits=hits,
            connectors_used=connectors_used,
            sources=sources,
            no_context=False,
            analytics=analytics,
            crisp_steps=crisp_steps,
        )

    def _message_metadata(
        self,
        sources: list[AssistantSource],
        analytics: AnalyticsPayload | None,
    ) -> dict | None:
        payload: dict = {}
        if sources:
            payload["sources"] = [s.model_dump(mode="json") for s in sources]
        if analytics:
            payload["analytics"] = analytics.model_dump(mode="json")
        return payload or None

    def _parse_message_metadata(self, metadata: dict | None) -> tuple[list[AssistantSource], AnalyticsPayload | None]:
        if not metadata:
            return [], None
        sources: list[AssistantSource] = []
        for item in metadata.get("sources") or []:
            try:
                sources.append(AssistantSource.model_validate(item))
            except Exception:
                continue
        analytics = None
        raw_analytics = metadata.get("analytics")
        if raw_analytics:
            try:
                analytics = AnalyticsPayload.model_validate(raw_analytics)
            except Exception:
                analytics = None
        return sources, analytics

    def _finalize_turn(
        self,
        prepared: PreparedAssistantTurn,
        answer: str,
        user_id: uuid.UUID | None,
        message: str,
        latency_ms: int,
    ) -> dict:
        assistant_msg = Message(
            conversation_id=prepared.conversation.id,
            role="assistant",
            content=answer,
            metadata_json=self._message_metadata(prepared.sources, prepared.analytics),
        )
        self.db.add(assistant_msg)
        self.db.commit()

        return {
            "conversation_id": prepared.conversation.id,
            "answer": answer,
            "sources": prepared.sources,
            "connectors_used": prepared.connectors_used,
            "latency_ms": latency_ms,
            "analytics": prepared.analytics.model_dump() if prepared.analytics else None,
        }

    def send_message(
        self,
        message: str,
        conversation_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        category: str | None = None,
    ) -> dict:
        start = time.perf_counter()
        prepared = self._prepare_turn(message, conversation_id, user_id, category)

        if prepared.static_answer:
            answer = prepared.static_answer
        else:
            try:
                answer = llm_provider.chat_completion(prepared.llm_messages or [], temperature=0.35)
            except Exception as exc:
                logger.error("Assistant LLM failed: %s", exc)
                answer = (
                    self._build_analytics_fallback_answer(prepared.analytics)
                    or "No pude procesar la consulta en este momento. Intenta de nuevo."
                )

        if not answer.strip():
            answer = NO_CONTEXT_RESPONSE

        latency_ms = int((time.perf_counter() - start) * 1000)
        return self._finalize_turn(prepared, answer, user_id, message, latency_ms)

    def stream_message(
        self,
        message: str,
        conversation_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        category: str | None = None,
    ) -> Generator[dict, None, None]:
        start = time.perf_counter()
        prepared = self._prepare_turn(message, conversation_id, user_id, category)

        yield {
            "type": "start",
            "conversation_id": str(prepared.conversation.id),
            "sources": [s.model_dump() for s in prepared.sources],
            "analytics": prepared.analytics.model_dump() if prepared.analytics else None,
            "crisp_steps": prepared.crisp_steps or [],
        }

        if prepared.static_answer:
            yield {"type": "token", "content": prepared.static_answer}
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._finalize_turn(prepared, prepared.static_answer, user_id, message, latency_ms)
            yield {"type": "done", "latency_ms": latency_ms}
            return

        full_parts: list[str] = []
        try:
            for token in llm_provider.chat_completion_stream(
                prepared.llm_messages or [],
                temperature=0.35,
            ):
                full_parts.append(token)
                yield {"type": "token", "content": token}
        except Exception as exc:
            logger.error("Assistant stream failed: %s", exc)
            fallback = (
                self._build_analytics_fallback_answer(prepared.analytics)
                or "No pude procesar la consulta en este momento. Intenta de nuevo."
            )
            if not full_parts:
                yield {"type": "token", "content": fallback}
            full_parts = full_parts or [fallback]

        answer = "".join(full_parts).strip() or NO_CONTEXT_RESPONSE
        latency_ms = int((time.perf_counter() - start) * 1000)
        self._finalize_turn(prepared, answer, user_id, message, latency_ms)
        yield {"type": "done", "latency_ms": latency_ms}

    def get_conversation_detail(self, conversation_id: uuid.UUID) -> dict | None:
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        messages = self.get_messages(conversation_id)
        message_items = []
        for m in messages:
            item = {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            if m.role == "assistant":
                sources, analytics = self._parse_message_metadata(m.metadata_json)
                item["sources"] = [s.model_dump(mode="json") for s in sources]
                item["analytics"] = analytics.model_dump(mode="json") if analytics else None
            message_items.append(item)

        return {
            "id": conversation.id,
            "status": conversation.status,
            "created_at": conversation.created_at,
            "messages": message_items,
        }
