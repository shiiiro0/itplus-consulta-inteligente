"""Pluggable data source connectors for the assistant."""

from itplus.app.connectors.base import (
    BaseConnector,
    ConnectorHit,
    ConnectorPhase,
    ConnectorResult,
    ConnectorStatus,
    QueryContext,
)
from itplus.app.connectors.registry import list_info, query_all, register

__all__ = [
    "BaseConnector",
    "ConnectorHit",
    "ConnectorPhase",
    "ConnectorResult",
    "ConnectorStatus",
    "QueryContext",
    "list_info",
    "query_all",
    "register",
]
