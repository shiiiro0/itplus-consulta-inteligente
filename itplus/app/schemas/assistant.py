from datetime import datetime
from uuid import UUID

from itplus.app.schemas.analytics import AnalyticsPayload
from pydantic import BaseModel, Field


class AssistantMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    conversation_id: UUID | None = None
    category: str | None = Field(
        default=None,
        description="Filtrar por categoría de conocimiento (ventas, productos, etc.)",
    )


class AssistantSource(BaseModel):
    source_id: str
    source_name: str
    excerpt: str
    page: int | None = None
    sheet: str | None = None
    score: float
    connector_key: str = "documents"


class ConnectorInfo(BaseModel):
    key: str
    label: str
    status: str
    hits_count: int = 0
    message: str | None = None


class AssistantMessageResponse(BaseModel):
    conversation_id: UUID
    answer: str
    sources: list[AssistantSource]
    connectors_used: list[ConnectorInfo]
    latency_ms: int
    analytics: AnalyticsPayload | None = None


class AssistantMessageItem(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
    sources: list[AssistantSource] = Field(default_factory=list)
    analytics: AnalyticsPayload | None = None


class AssistantConversationResponse(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    messages: list[AssistantMessageItem]
