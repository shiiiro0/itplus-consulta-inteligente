"""Connector registry — register and resolve data source plugins."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from itplus.app.connectors.base import BaseConnector, ConnectorResult, QueryContext

logger = logging.getLogger(__name__)

_connectors: dict[str, "BaseConnector"] = {}


def register(connector: "BaseConnector") -> None:
    _connectors[connector.key] = connector
    logger.debug("Connector registrado: %s", connector.key)


def get(key: str) -> "BaseConnector | None":
    return _connectors.get(key)


def list_all() -> list["BaseConnector"]:
    return list(_connectors.values())


def list_info() -> list[dict]:
    return [c.info() for c in _connectors.values()]


def query_all(db: "Session", ctx: "QueryContext") -> list["ConnectorResult"]:
    from itplus.app.connectors.document import DocumentConnector
    from itplus.app.connectors.erp_api import ErpApiConnector

    results: list[ConnectorResult] = []
    for cls in (DocumentConnector, ErpApiConnector):
        connector = cls(db)
        if connector.phase.value == "planned":
            continue
        try:
            results.append(connector.query(ctx))
        except Exception as exc:
            logger.warning("Connector %s falló: %s", connector.key, exc)
            from itplus.app.connectors.base import ConnectorResult, ConnectorStatus

            results.append(
                ConnectorResult(
                    connector_key=connector.key,
                    connector_label=connector.label,
                    status=ConnectorStatus.ERROR,
                    message=str(exc),
                )
            )
    return results
