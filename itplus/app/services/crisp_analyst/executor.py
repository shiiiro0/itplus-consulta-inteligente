"""CRISP-DM Phase 4 execution: run planned SQL safely (SELECT only)."""

from __future__ import annotations

import re
from typing import Any

import duckdb

from itplus.app.services.crisp_analyst.planner import QueryPlan

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|COPY|ATTACH|DETACH|EXPORT|IMPORT|LOAD|INSTALL|PRAGMA)\b",
    re.IGNORECASE,
)


def execute_plan(con: duckdb.DuckDBPyConnection, plan: QueryPlan) -> list[dict[str, Any]]:
    sql = plan.sql.strip()
    if _FORBIDDEN.search(sql):
        raise ValueError("Solo se permiten consultas SELECT")
    if not sql.upper().lstrip().startswith("SELECT"):
        raise ValueError("La consulta debe comenzar con SELECT")

    rows = con.execute(sql).fetchall()
    cols = [d[0] for d in con.description or []]
    return [dict(zip(cols, row)) for row in rows]
