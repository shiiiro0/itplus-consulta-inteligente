from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    document_id: UUID
    document_name: str
    excerpt: str
    page: int | None = None
    score: float


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]


class QueryHistoryItem(BaseModel):
    id: UUID
    question: str
    answer_summary: str
    sources_count: int
    latency_ms: int
    model_used: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
