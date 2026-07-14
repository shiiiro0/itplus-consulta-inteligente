"""Structured analytics payloads for Phase 2 assistant responses."""

from pydantic import BaseModel, Field


class ChartDataset(BaseModel):
    label: str
    values: list[float]


class ChartSpec(BaseModel):
    id: str
    chart_type: str = Field(description="bar | line | pie")
    title: str
    labels: list[str]
    datasets: list[ChartDataset]
    value_format: str = Field(default="number", description="number | clp | pct")
    optional: bool = Field(default=False, description="Solo si el gerente lo pide (ej. tendencia lineal)")


class TableSpec(BaseModel):
    id: str
    title: str
    columns: list[str]
    rows: list[list[str]]


class ComparisonSpec(BaseModel):
    label: str
    period_a: str
    period_b: str
    value_a: float
    value_b: float
    change_pct: float
    unit: str = "clp"


class AnalyticsPayload(BaseModel):
    charts: list[ChartSpec] = Field(default_factory=list)
    tables: list[TableSpec] = Field(default_factory=list)
    comparisons: list[ComparisonSpec] = Field(default_factory=list)
