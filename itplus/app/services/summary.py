"""Technical summary generation after chat closure."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from itplus.app.models.conversation import Conversation, Message, Summary
from itplus.app.prompts.summary import SUMMARY_SYSTEM_PROMPT
from itplus.app.services.llm_provider import llm_provider

logger = logging.getLogger(__name__)


class SummaryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _format_conversation_history(self, messages: list[Message]) -> str:
        lines: list[str] = []
        for msg in messages:
            if msg.role in ("user", "assistant"):
                role_label = "Usuario" if msg.role == "user" else "ITPlusBot"
                lines.append(f"{role_label}: {msg.content}")
        return "\n\n".join(lines)

    def generate_summary(self, conversation_id: uuid.UUID) -> Summary | None:
        conversation = (
            self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )
        if not conversation:
            return None

        existing = self.db.query(Summary).filter(Summary.conversation_id == conversation_id).first()
        if existing:
            return existing

        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

        history = self._format_conversation_history(messages)
        if not history.strip():
            return None

        llm_messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Genera el resumen técnico de esta conversación:\n\n{history}",
            },
        ]

        try:
            summary_content = llm_provider.chat_completion(llm_messages, temperature=0.1)
        except Exception as exc:
            # Antes esto se guardaba como un Summary "válido" con un mensaje
            # de error dentro. El chequeo de "existing" de arriba lo trataba
            # como ya generado para siempre, así que un fallo transitorio del
            # LLM dejaba a la conversación sin resumen real para siempre, sin
            # forma de reintentar. Ahora no persistimos nada: la próxima vez
            # que se llame a generate_summary() para esta conversación, lo
            # va a intentar de nuevo de verdad.
            logger.error("Summary generation failed for %s: %s", conversation_id, exc)
            return None

        summary = Summary(conversation_id=conversation_id, content=summary_content)
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        return summary

    def get_summary(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> Summary | None:
        query = self.db.query(Summary).filter(Summary.conversation_id == conversation_id)
        if user_id is not None:
            query = query.join(Conversation, Conversation.id == Summary.conversation_id).filter(
                Conversation.user_id == user_id
            )
        return query.first()

    def generate_summary_async(self, conversation_id: uuid.UUID) -> None:
        """Dispatch summary generation to Celery worker."""
        from itplus.app.workers.index_document import generate_summary_task

        generate_summary_task.delay(str(conversation_id))
