"""Canonical KPI dictionary for the managerial assistant (ITPlus).

These definitions are the single source of truth for what a metric *means*.
Computable KPIs are executed by CRISP (DuckDB SQL). Non-computable ones are
still declared so the LLM does not invent alternate formulas.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KpiDefinition:
    key: str
    name: str
    formula: str
    unit: str
    aliases: tuple[str, ...]
    computable: bool
    notes: str = ""


# Official ITPlus KPI catalog (extend carefully — aliases drive matching).
KPI_CATALOG: tuple[KpiDefinition, ...] = (
    KpiDefinition(
        key="ingresos_totales",
        name="Ingresos totales",
        formula="SUM(precio × cantidad) en CLP sobre el período filtrado",
        unit="clp",
        aliases=("ingreso", "ingresos", "factur", "venta", "ventas", "revenue", "cuanto vend", "cuánto vend"),
        computable=True,
        notes="Por defecto 'ventas' = ingresos, no unidades ni margen.",
    ),
    KpiDefinition(
        key="ticket_promedio",
        name="Ticket promedio",
        formula="SUM(ingresos) / COUNT(DISTINCT pedido) — si no hay id de pedido: SUM(ingresos) / COUNT(filas)",
        unit="clp",
        aliases=("ticket", "ticket promedio", "ticket medio", "aov", "average order"),
        computable=True,
        notes="Proxy por fila si el dataset no trae order_id.",
    ),
    KpiDefinition(
        key="unidades_vendidas",
        name="Unidades vendidas",
        formula="SUM(cantidad) sobre el período filtrado",
        unit="units",
        aliases=("unidad", "unidades", "qty", "cantidad vend", "volumen de unidades"),
        computable=True,
    ),
    KpiDefinition(
        key="ingresos_por_categoria",
        name="Ingresos por categoría",
        formula="SUM(ingresos) GROUP BY categoría/familia",
        unit="clp",
        aliases=("categoria", "categoría", "familia", "mix de producto", "mix de categoria"),
        computable=True,
    ),
    KpiDefinition(
        key="ingresos_por_ciudad",
        name="Ingresos por ciudad/región",
        formula="SUM(ingresos) GROUP BY ciudad/región",
        unit="clp",
        aliases=("ciudad", "region", "región", "zona"),
        computable=True,
    ),
    KpiDefinition(
        key="margen_bruto",
        name="Margen bruto",
        formula="(ingresos − costo) / ingresos",
        unit="pct",
        aliases=("margen", "margen bruto", "gross margin"),
        computable=False,
        notes="Requiere columna de costo. Hoy no está en los datasets típicos → declarar indisponible.",
    ),
)


def match_kpis(question: str) -> list[KpiDefinition]:
    """Return KPI definitions whose aliases appear in the question (stable order)."""
    q = (question or "").lower()
    if not q:
        return []
    hits: list[KpiDefinition] = []
    for kpi in KPI_CATALOG:
        if any(alias in q for alias in kpi.aliases):
            hits.append(kpi)
    return hits


def format_kpi_context(kpis: list[KpiDefinition]) -> str:
    """Compact block for the LLM: official formulas, no invention."""
    if not kpis:
        return ""
    lines = [
        "## DICCIONARIO KPI OFICIAL (usa estas fórmulas; no inventes otras)",
    ]
    for kpi in kpis:
        avail = "computable ahora" if kpi.computable else "NO computable con los datos actuales"
        lines.append(f"- {kpi.name} [{kpi.key}] ({avail})")
        lines.append(f"  Fórmula: {kpi.formula}")
        lines.append(f"  Unidad: {kpi.unit}")
        if kpi.notes:
            lines.append(f"  Nota: {kpi.notes}")
        if not kpi.computable:
            lines.append(
                "  Si el gerente pregunta por este KPI, dilo con claridad y qué columna falta "
                "(p. ej. costo) — no inventes el margen."
            )
    return "\n".join(lines)
