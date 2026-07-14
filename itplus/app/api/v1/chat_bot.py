"""ITPlusBot chat endpoints (Motor A)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from itplus.app.api.deps import get_current_user, get_optional_user
from itplus.app.core.database import get_db
from itplus.app.core.phases import BOT_KNOWLEDGE_CATEGORIES, CURRENT_PHASE
from itplus.app.models.user import User
from itplus.app.schemas.chat_bot import (
    BotMessageRequest,
    BotMessageResponse,
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    SummaryResponse,
)
from itplus.app.services.conversation import ConversationService
from itplus.app.services.summary import SummaryService

router = APIRouter()


def _turn_to_response(result) -> BotMessageResponse:
    return BotMessageResponse(
        conversation_id=result.conversation.id,
        response=result.response,
        is_finished=result.is_finished,
        sources=result.sources,
        ticket_reference=result.ticket_reference,
        escalated=result.escalated,
    )


@router.get("/roadmap")
def bot_roadmap():
    return {
        "current_phase": CURRENT_PHASE,
        "knowledge_categories": BOT_KNOWLEDGE_CATEGORIES,
    }


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    payload: CreateConversationRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    svc = ConversationService(db)
    conv = svc.create_conversation(
        user_id=current_user.id if current_user else None,
        context_type=payload.context_type if payload else None,
        context_id=payload.context_id if payload else None,
    )
    return conv


@router.post("", response_model=BotMessageResponse)
def send_message(
    payload: BotMessageRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    svc = ConversationService(db)
    try:
        result = svc.send_message(
            message=payload.message,
            conversation_id=payload.conversation_id,
            user_id=current_user.id if current_user else None,
            category=payload.category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return _turn_to_response(result)


@router.post("/conversations/{conversation_id}/finish", response_model=BotMessageResponse)
def finish_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    svc = ConversationService(db)
    try:
        result = svc.finish_conversation_manually(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return _turn_to_response(result)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    svc = ConversationService(db)
    conversation = svc.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")

    messages = svc.get_messages(conversation_id)
    visible_messages = [m for m in messages if m.role != "system"]

    return ConversationDetailResponse(
        conversation=ConversationResponse.model_validate(conversation),
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                sources=svc.message_sources(m),
            )
            for m in visible_messages
        ],
    )


@router.get("/conversations/{conversation_id}/summary", response_model=SummaryResponse)
def get_summary(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    summary_svc = SummaryService(db)
    summary = summary_svc.get_summary(conversation_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resumen no disponible aún. La conversación puede no haber finalizado.",
        )
    return summary
