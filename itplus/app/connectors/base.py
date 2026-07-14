"""Base types for pluggable data source connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConnectorPhase(str, Enum):
    ACTIVE = "active"
    STUB = "stub"
    PLANNED = "planned"


class ConnectorStatus(str, Enum):
    READY = "ready"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ConnectorHit:
    source_id: str
    source_name: str
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorResult:
    connector_key: str
    connector_label: str
    status: ConnectorStatus
    hits: list[ConnectorHit] = field(default_factory=list)
    message: str | None = None


@dataclass
class QueryContext:
    question: str
    category: str | None = None
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    user_id: str | None = None


class BaseConnector(ABC):
    key: str
    label: str
    phase: ConnectorPhase = ConnectorPhase.ACTIVE
    description: str = ""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the connector can run (configured and enabled)."""

    @abstractmethod
    def query(self, ctx: QueryContext) -> ConnectorResult:
        """Fetch relevant data for the user question."""

    def info(self) -> dict[str, Any]:
        status = ConnectorStatus.READY if self.is_available() else ConnectorStatus.NOT_CONFIGURED
        if self.phase == ConnectorPhase.STUB:
            status = ConnectorStatus.NOT_CONFIGURED
        return {
            "key": self.key,
            "label": self.label,
            "phase": self.phase.value,
            "description": self.description,
            "status": status.value,
            "available": self.is_available(),
        }
