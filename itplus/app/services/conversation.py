"""ITPlusBot conversation service (Motor A) with knowledge-base retrieval."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from itplus.app.connectors.base import QueryContext
from itplus.app.connectors.erp_api import ErpApiConnector
from itplus.app.models.conversation import Conversation, Message
from itplus.app.prompts.itplus_bot import CHAT_FINISHED_MARKER, ITPLUS_BOT_SYSTEM_PROMPT
from itplus.app.schemas.chat_query import SourceCitation
from itplus.app.services.llm_provider import llm_provider
from itplus.app.services.retrieval import RetrievalService
from itplus.app.services.summary import SummaryService
from itplus.app.utils.document_location import format_document_location, parse_document_location
from itplus.app.utils.small_talk import is_small_talk

logger = logging.getLogger(__name__)

DEFAULT_BOT_CATEGORY = "soporte"


@dataclass
class BotTurnResult:
    conversation: Conversation
    response: str
    is_finished: bool
    sources: list[SourceCitation] = field(default_factory=list)
    ticket_reference: str | None = None
    escalated: bool = False
    connector_note: str | None = None


class ConversationService:
    FINISHED_PATTERN = re.compile(re.escape(CHAT_FINISHED_MARKER), re.IGNORECASE)
    ESCALATION_PATTERN = re.compile(
        r"escalar|t[eé]cnico humano|equipo de soporte|no hay procedimiento documentado",
        re.IGNORECASE,
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self.summary_service = SummaryService(db)
        self.retrieval = RetrievalService(db)
        self.erp_connector = ErpApiConnector(db)

    def create_conversation(
        self,
        user_id: uuid.UUID | None = None,
        context_type: str | None = None,
        context_id: str | None = None,
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            context_type=context_type,
            context_id=context_id,
            status="active",
        )
        self.db.add(conversation)

        system_msg = Message(
            conversation=conversation,
            role="system",
            content=ITPLUS_BOT_SYSTEM_PROMPT,
        )
        self.db.add(system_msg)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()

    def get_messages(self, conversation_id: uuid.UUID) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

    def _resolve_category(self, category: str | None) -> str:
        cat = (category or DEFAULT_BOT_CATEGORY).strip().lower()
        return cat or DEFAULT_BOT_CATEGORY

    def _generate_ticket_reference(self, conversation_id: uuid.UUID) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        suffix = str(conversation_id).replace("-", "")[:6].upper()
        return f"ITP-{stamp}-{suffix}"

    def _hits_to_sources(self, hits: list[dict]) -> list[SourceCitation]:
        sources: list[SourceCitation] = []
        for hit in hits:
            page, sheet = parse_document_location(hit)
            excerpt = hit["content"][:300] + ("..." if len(hit["content"]) > 300 else "")
            sources.append(
                SourceCitation(
                    document_id=hit["document_id"],
                    document_name=hit["document_name"],
                    excerpt=excerpt,
                    page=page,
                    sheet=sheet,
                    score=hit["score"],
                )
            )
        return sources

    def _sources_to_metadata(self, sources: list[SourceCitation]) -> dict:
        return {
            "sources": [s.model_dump(mode="json") for s in sources],
            "sources_count": len(sources),
        }

    def _metadata_to_sources(self, metadata: dict | None) -> list[SourceCitation]:
        if not metadata:
            return []
        raw = metadata.get("sources") or []
        out: list[SourceCitation] = []
        for item in raw:
            try:
                out.append(SourceCitation.model_validate(item))
            except Exception:
                continue
        return out

    def _build_context(self, hits: list[dict], connector_note: str | None = None) -> str:
        parts: list[str] = []
        if connector_note:
            parts.append(f"[Sistemas conectados]\n{connector_note}")
        for i, hit in enumerate(hits, 1):
            page, sheet = parse_document_location(hit)
            loc = format_document_location(page, sheet)
            parts.append(
                f"[Fuente {i}: {hit['document_name']}{loc}]\n{hit['content']}"
            )
        return "\n\n---\n\n".join(parts)

    def _build_llm_messages(
        self,
        messages: list[Message],
        user_message: str,
        context_block: str,
        current_user_msg_id: uuid.UUID,
    ) -> list[dict[str, str]]:
        llm_messages: list[dict[str, str]] = [{"role": "system", "content": ITPLUS_BOT_SYSTEM_PROMPT}]

        prior = [
            m for m in messages
            if m.role in ("user", "assistant") and m.id != current_user_msg_id
        ]
        for msg in prior:
            llm_messages.append({"role": msg.role, "content": msg.content})

        if context_block.strip():
            user_content = (
                f"Base de conocimiento relevante:\n\n{context_block}\n\n"
                f"Mensaje del usuario: {user_message}"
            )
        else:
            user_content = (
                "No se encontraron fragmentos relevantes en la base de conocimiento para este mensaje.\n\n"
                f"Mensaje del usuario: {user_message}"
            )

        llm_messages.append({"role": "user", "content": user_content})
        return llm_messages

    def is_finished_response(self, response: str) -> bool:
        return bool(self.FINISHED_PATTERN.search(response))

    def _maybe_escalated(self, response: str, hits: list[dict]) -> bool:
        if not hits and self.ESCALATION_PATTERN.search(response):
            return True
        return bool(re.search(r"escalar|ticket|t[eé]cnico humano", response, re.IGNORECASE))

    def _query_erp_note(self, message: str, category: str | None) -> str | None:
        ctx = QueryContext(question=message, category=category)
        result = self.erp_connector.query(ctx)
        if result.hits:
            lines = [f"- {hit.content}" for hit in result.hits[:3]]
            return "Datos del sistema conectado:\n" + "\n".join(lines)
        if self.erp_connector.is_available() and result.message:
            return result.message
        if not self.erp_connector.is_available():
            return (
                "Conector ERP/API no configurado aún. "
                "Responde solo con la base documental disponible."
            )
        return None

    def send_message(
        self,
        message: str,
        conversation_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        category: str | None = None,
    ) -> BotTurnResult:
        if conversation_id:
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError("Conversation not found")
            if conversation.status == "finished":
                raise ValueError("Conversation already finished")
        else:
            conversation = self.create_conversation(user_id=user_id, context_type="bot")

        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        self.db.add(user_msg)
        if not conversation.title:
            conversation.title = (message or "").strip().replace("\n", " ")[:77] + (
                "..." if len((message or "").strip()) > 80 else ""
            )
        self.db.flush()

        resolved_category = self._resolve_category(category)
        hits: list[dict] = []
        connector_note: str | None = None

        if not is_small_talk(message):
            hits = self.retrieval.search_multi(
                message,
                categories=[resolved_category],
                top_k=5,
            )
            connector_note = self._query_erp_note(message, resolved_category)

        context_block = self._build_context(hits, connector_note)
        all_messages = self.get_messages(conversation.id)
        llm_messages = self._build_llm_messages(all_messages, message, context_block, user_msg.id)

        assistant_response = llm_provider.chat_completion(llm_messages, temperature=0.25)
        sources = self._hits_to_sources(hits)

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_response,
            metadata_json=self._sources_to_metadata(sources) if sources else None,
        )
        self.db.add(assistant_msg)

        is_finished = self.is_finished_response(assistant_response)
        ticket_reference = conversation.ticket_reference
        escalated = self._maybe_escalated(assistant_response, hits)

        if is_finished and not ticket_reference:
            ticket_reference = self._generate_ticket_reference(conversation.id)
            conversation.ticket_reference = ticket_reference
            conversation.status = "finished"
            conversation.finished_at = datetime.now(timezone.utc)
            if ticket_reference not in assistant_response:
                assistant_response = (
                    f"{assistant_response.rstrip()}\n\n"
                    f"Tu ticket de seguimiento es: {ticket_reference}"
                )
                assistant_msg.content = assistant_response
        elif is_finished:
            conversation.status = "finished"
            conversation.finished_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(conversation)

        if is_finished:
            try:
                self.summary_service.generate_summary_async(conversation.id)
            except Exception as exc:
                logger.warning("Could not schedule summary generation: %s", exc)
                self.summary_service.generate_summary(conversation.id)

        return BotTurnResult(
            conversation=conversation,
            response=assistant_response,
            is_finished=is_finished,
            sources=sources,
            ticket_reference=ticket_reference if is_finished else None,
            escalated=escalated,
            connector_note=connector_note,
        )

    def finish_conversation_manually(self, conversation_id: uuid.UUID) -> BotTurnResult:
        """Allow user to manually finish chat."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        if conversation.status == "finished":
            raise ValueError("Conversation already finished")

        ticket_reference = conversation.ticket_reference or self._generate_ticket_reference(
            conversation.id
        )

        finish_message = (
            "El usuario ha solicitado finalizar la conversación. "
            "Gracias por confiar en ITPlusBot. Hemos registrado tu caso "
            f"con el ticket {ticket_reference}. Un técnico revisará tu solicitud pronto. "
            f"{CHAT_FINISHED_MARKER}"
        )

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=finish_message,
        )
        self.db.add(assistant_msg)
        conversation.status = "finished"
        conversation.ticket_reference = ticket_reference
        conversation.finished_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(conversation)

        try:
            self.summary_service.generate_summary_async(conversation.id)
        except Exception:
            self.summary_service.generate_summary(conversation.id)

        return BotTurnResult(
            conversation=conversation,
            response=finish_message,
            is_finished=True,
            sources=[],
            ticket_reference=ticket_reference,
            escalated=True,
        )

    def message_sources(self, message: Message) -> list[SourceCitation]:
        return self._metadata_to_sources(message.metadata_json)
