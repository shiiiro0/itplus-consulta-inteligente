"""ITPlusBot conversation service (Motor A)."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from itplus.app.models.conversation import Conversation, Message
from itplus.app.prompts.itplus_bot import CHAT_FINISHED_MARKER, ITPLUS_BOT_SYSTEM_PROMPT
from itplus.app.services.llm_provider import llm_provider
from itplus.app.services.summary import SummaryService

logger = logging.getLogger(__name__)


class ConversationService:
    FINISHED_PATTERN = re.compile(re.escape(CHAT_FINISHED_MARKER), re.IGNORECASE)

    def __init__(self, db: Session) -> None:
        self.db = db
        self.summary_service = SummaryService(db)

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

    def _build_llm_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        llm_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg.role in ("user", "assistant", "system"):
                llm_messages.append({"role": msg.role, "content": msg.content})
        return llm_messages

    def is_finished_response(self, response: str) -> bool:
        return bool(self.FINISHED_PATTERN.search(response))

    def send_message(
        self,
        message: str,
        conversation_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> tuple[Conversation, str, bool]:
        if conversation_id:
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError("Conversation not found")
            if conversation.status == "finished":
                raise ValueError("Conversation already finished")
        else:
            conversation = self.create_conversation(user_id=user_id)

        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        self.db.add(user_msg)
        self.db.flush()

        all_messages = self.get_messages(conversation.id)
        llm_messages = self._build_llm_messages(all_messages)

        assistant_response = llm_provider.chat_completion(llm_messages)

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_response,
        )
        self.db.add(assistant_msg)

        is_finished = self.is_finished_response(assistant_response)
        if is_finished:
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

        return conversation, assistant_response, is_finished

    def finish_conversation_manually(self, conversation_id: uuid.UUID) -> tuple[Conversation, str, bool]:
        """Allow user to manually finish chat."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        if conversation.status == "finished":
            raise ValueError("Conversation already finished")

        finish_message = (
            "El usuario ha solicitado finalizar la conversación. "
            "Gracias por compartir la información. Un técnico revisará tu caso pronto. "
            f"{CHAT_FINISHED_MARKER}"
        )

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=finish_message,
        )
        self.db.add(assistant_msg)
        conversation.status = "finished"
        conversation.finished_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(conversation)

        try:
            self.summary_service.generate_summary_async(conversation.id)
        except Exception:
            self.summary_service.generate_summary(conversation.id)

        return conversation, finish_message, True
