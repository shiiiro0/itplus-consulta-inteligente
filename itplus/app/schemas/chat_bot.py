from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BotMessageRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(..., min_length=1, max_length=8000)


class BotMessageResponse(BaseModel):
    conversation_id: UUID
    response: str
    is_finished: bool


class CreateConversationRequest(BaseModel):
    context_type: str | None = None
    context_id: str | None = None


class ConversationResponse(BaseModel):
    id: UUID
    status: str
    context_type: str | None
    context_id: str | None
    created_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]


class SummaryResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
