"""Schemas for unified chat history."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ChatHistoryItem(BaseModel):
    id: str
    chat_type: str
    chat_type_label: str
    title: str
    preview: str
    message_count: int
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    sources_count: int | None = None


class ChatHistoryListResponse(BaseModel):
    items: list[ChatHistoryItem]
    total: int


class ConsultaDetailResponse(BaseModel):
    id: str
    chat_type: str
    question: str
    answer: str
    sources_count: int
    created_at: datetime
    entries: list[dict] | None = None


class RenameChatRequest(BaseModel):
    title: str


class ChatExportResponse(BaseModel):
    filename: str
    content: str
