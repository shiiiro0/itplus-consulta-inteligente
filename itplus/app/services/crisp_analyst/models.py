"""Data models for the CRISP-DM analyst pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from itplus.app.schemas.analytics import AnalyticsPayload


@dataclass
class CrispStep:
    phase: str
    label: str
    detail: str = ""


@dataclass
class DatasetProfile:
    document_id: UUID
    document_name: str
    row_count: int
    columns: list[str]
    date_column: str | None = None
    quantity_column: str | None = None
    price_column: str | None = None
    category_column: str | None = None
    city_column: str | None = None
    product_column: str | None = None
    date_min: str | None = None
    date_max: str | None = None
    revenue_expression: str = "revenue"


@dataclass
class CrispPipelineResult:
    success: bool
    steps: list[CrispStep] = field(default_factory=list)
    llm_context: str = ""
    analytics: AnalyticsPayload | None = None
    source_document_id: UUID | None = None
    source_document_name: str | None = None
    metrics: dict = field(default_factory=dict)
