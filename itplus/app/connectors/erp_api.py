"""ERP / external API connector stub (Phase 3 — ready to plug in)."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from itplus.app.connectors.base import (
    BaseConnector,
    ConnectorPhase,
    ConnectorResult,
    ConnectorStatus,
    QueryContext,
)


class ErpApiConnector(BaseConnector):
    key = "erp_api"
    label = "ERP / APIs externas"
    phase = ConnectorPhase.STUB
    description = (
        "Conector preparado para sistemas como Canontex, APIs REST o bases de datos. "
        "Se activará configurando ERP_API_URL y credenciales en el entorno."
    )

    def __init__(self, db: Session) -> None:
        self.db = db

    def is_available(self) -> bool:
        return bool(os.environ.get("ERP_API_URL", "").strip())

    def query(self, ctx: QueryContext) -> ConnectorResult:
        if not self.is_available():
            return ConnectorResult(
                connector_key=self.key,
                connector_label=self.label,
                status=ConnectorStatus.NOT_CONFIGURED,
                hits=[],
                message=(
                    "Conector ERP/API no configurado. "
                    "Define ERP_API_URL en .env cuando esté listo para integrar."
                ),
            )

        # Extension point: implement HTTP/DB queries here in Phase 3.
        return ConnectorResult(
            connector_key=self.key,
            connector_label=self.label,
            status=ConnectorStatus.NOT_CONFIGURED,
            hits=[],
            message="Conector ERP en desarrollo (Fase 3).",
        )
