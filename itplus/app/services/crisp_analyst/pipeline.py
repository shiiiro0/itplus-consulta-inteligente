"""CRISP-DM orchestrator: business → data → prepare → model → evaluate → deploy."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from itplus.app.core.kpis import format_kpi_context, match_kpis
from itplus.app.schemas.analytics import (
    AnalyticsPayload,
    ChartDataset,
    ChartSpec,
    ComparisonSpec,
    TableSpec,
)
from itplus.app.services.crisp_analyst.executor import execute_plan
from itplus.app.services.crisp_analyst.forecast import ForecastResult, build_revenue_forecast
from itplus.app.services.crisp_analyst.models import CrispPipelineResult, CrispStep
from itplus.app.services.crisp_analyst.planner import plan_query
from itplus.app.services.crisp_analyst.profiler import profile_step, select_best_dataset
from itplus.app.services.crisp_analyst.registry import connect_dataset, list_ready_datasets, register_document_dataset
from itplus.app.services.document_analytics import resolve_retrieval_question

logger = logging.getLogger(__name__)


def _business_step(question: str, resolved: str) -> CrispStep:
    detail = resolved[:120] + ("…" if len(resolved) > 120 else "")
    if detail != question[:120]:
        detail = f"Intención: {detail}"
    else:
        detail = f"Pregunta analítica: {detail}"
    return CrispStep(
        phase="business_understanding",
        label="Comprensión del negocio",
        detail=detail,
    )


def _prepare_step() -> CrispStep:
    return CrispStep(
        phase="data_preparation",
        label="Preparación de datos",
        detail="Vista data_clean con ingreso (precio × cantidad) y fechas normalizadas",
    )


def _model_step(intent: str) -> CrispStep:
    labels = {
        "total_revenue": "Total de ingresos",
        "ticket_average": "Ticket promedio",
        "units_sold": "Unidades vendidas",
        "by_category": "Desglose por categoría",
        "by_city": "Desglose por ciudad",
        "by_month": "Serie mensual",
        "forecast_revenue": "Proyección de ingresos (próximo mes)",
        "compare_quarters": "Comparativo trimestral",
        "compare_halves": "Comparativo semestral",
        "top_products": "Ranking de productos",
    }
    return CrispStep(
        phase="modeling",
        label="Modelado (SQL)",
        detail=labels.get(intent, intent),
    )


def _evaluate_step(rows: list[dict[str, Any]]) -> CrispStep:
    if not rows:
        return CrispStep(
            phase="evaluation",
            label="Evaluación",
            detail="Sin filas — revisar filtros o rango de fechas",
        )
    if len(rows) == 1:
        val = rows[0].get("value")
        if val is not None:
            try:
                detail = f"Resultado validado: {float(val):,.2f}"
            except (TypeError, ValueError):
                detail = f"Resultado validado: {val}"
            return CrispStep(phase="evaluation", label="Evaluación", detail=detail)
    return CrispStep(
        phase="evaluation",
        label="Evaluación",
        detail=f"{len(rows)} grupos calculados con SQL determinista",
    )


def _build_analytics(
    plan,
    rows: list[dict[str, Any]],
    doc_name: str,
    forecast: ForecastResult | None = None,
) -> AnalyticsPayload | None:
    if not rows:
        return None

    if plan.intent in ("total_revenue", "ticket_average", "units_sold") and len(rows) == 1:
        val = float(rows[0].get("value") or 0)
        metric_label = {
            "total_revenue": "Ingresos totales",
            "ticket_average": "Ticket promedio",
            "units_sold": "Unidades vendidas",
        }[plan.intent]
        value_fmt = f"{val:,.0f}" if plan.intent == "units_sold" else f"${val:,.0f}"
        col2 = "Unidades" if plan.intent == "units_sold" else "Valor (CLP)"
        return AnalyticsPayload(
            tables=[
                TableSpec(
                    id=f"crisp_{plan.intent}",
                    title=f"{metric_label} — {doc_name}",
                    columns=["Métrica", col2],
                    rows=[[metric_label, value_fmt]],
                )
            ],
        )

    labels = [str(r.get("label", "")) for r in rows]
    values = [float(r.get("value") or 0) for r in rows]

    charts: list[ChartSpec] = []
    if plan.intent == "forecast_revenue" and forecast is not None:
        hist_labels = [str(r["label"]) for r in forecast.rows if r.get("kind") == "historico"]
        hist_values = [float(r["value"]) for r in forecast.rows if r.get("kind") == "historico"]
        # Serie histórica + punto de proyección (último valor = forecast).
        chart_labels = hist_labels + [forecast.horizon_label]
        chart_values = hist_values + [forecast.point_forecast]
        charts.append(
            ChartSpec(
                id="crisp_forecast_revenue",
                chart_type="line",
                title=plan.chart_title or "Proyección de ingresos",
                labels=chart_labels,
                datasets=[ChartDataset(label="Ingresos (CLP)", values=chart_values)],
                value_format="clp",
            )
        )
    elif plan.chart_type and labels:
        charts.append(
            ChartSpec(
                id=f"crisp_{plan.intent}",
                chart_type=plan.chart_type,
                title=plan.chart_title or "Análisis",
                labels=labels,
                datasets=[ChartDataset(label=plan.group_label or "Valor", values=values)],
                value_format="clp",
            )
        )
    elif plan.intent in ("compare_quarters", "compare_halves") and len(rows) >= 2:
        charts.append(
            ChartSpec(
                id=f"crisp_{plan.intent}",
                chart_type="bar",
                title=plan.chart_title or "Comparativo",
                labels=labels,
                datasets=[ChartDataset(label=plan.group_label or "Valor", values=values)],
                value_format="clp",
                optional=True,
            )
        )

    comparisons: list[ComparisonSpec] = []
    if plan.intent in ("compare_quarters", "compare_halves") and len(rows) >= 2:
        a, b = rows[0], rows[1]
        value_a = float(a.get("value") or 0)
        value_b = float(b.get("value") or 0)
        if value_a > 0:
            change = (value_b - value_a) / value_a * 100
            comparisons.append(
                ComparisonSpec(
                    label=plan.chart_title or "Comparativo",
                    period_a=str(a.get("label", "")),
                    period_b=str(b.get("label", "")),
                    value_a=value_a,
                    value_b=value_b,
                    change_pct=round(change, 1),
                    unit="clp",
                )
            )

    if plan.intent == "forecast_revenue" and forecast is not None:
        table_rows = [
            [
                str(r.get("label", "")),
                "Histórico" if r.get("kind") == "historico" else "Proyección",
                f"${float(r.get('value') or 0):,.0f}",
            ]
            for r in forecast.rows
        ]
        tables = [
            TableSpec(
                id="crisp_forecast_table",
                title="Serie mensual + proyección",
                columns=["Mes", "Tipo", "Ingreso (CLP)"],
                rows=table_rows,
            ),
            TableSpec(
                id="crisp_forecast_summary",
                title=f"Proyección {forecast.horizon_label}",
                columns=["Concepto", "Valor"],
                rows=[
                    ["Punto estimado", f"${forecast.point_forecast:,.0f}"],
                    ["Banda baja", f"${forecast.low:,.0f}"],
                    ["Banda alta", f"${forecast.high:,.0f}"],
                    ["Método", forecast.method_label],
                    [
                        "MAPE backtest",
                        f"{forecast.mape_pct:.1f}%" if forecast.mape_pct is not None else "N/D (serie corta)",
                    ],
                ],
            ),
        ]
        return AnalyticsPayload(charts=charts, tables=tables, comparisons=comparisons)

    table_rows = [
        [str(r.get("label", "")), f"${float(r.get('value') or 0):,.0f}"]
        for r in rows[:12]
    ]
    tables = [
        TableSpec(
            id=f"crisp_table_{plan.intent}",
            title=plan.chart_title or "Detalle analítico",
            columns=[plan.group_label or "Grupo", "Ingreso (CLP)"],
            rows=table_rows,
        )
    ]

    if not charts and not tables and not comparisons:
        return None

    return AnalyticsPayload(charts=charts, tables=tables, comparisons=comparisons)


def _build_llm_context(
    doc_name: str,
    steps: list[CrispStep],
    plan,
    rows: list[dict[str, Any]],
    profile=None,
    question: str = "",
    forecast: ForecastResult | None = None,
) -> str:
    # No exponer el nombre de archivo al LLM (las fuentes van a la UI).
    lines = [
        "=== Análisis CRISP-DM (DuckDB — no inventar cifras) ===",
        "Dataset: tabular consolidado de la empresa",
    ]
    kpi_block = format_kpi_context(match_kpis(question))
    if kpi_block:
        lines.append(kpi_block)

    if profile is not None:
        coverage_bits: list[str] = []
        if getattr(profile, "date_min", None) and getattr(profile, "date_max", None):
            coverage_bits.append(f"cobertura {profile.date_min} → {profile.date_max}")
        if getattr(profile, "row_count", None):
            coverage_bits.append(f"{profile.row_count:,} filas".replace(",", "."))
        if coverage_bits:
            lines.append("COBERTURA DE DATOS: " + "; ".join(coverage_bits) + ".")
            lines.append(
                "LIMITACIÓN: el análisis solo cubre ese rango; no extrapoles fuera de él "
                "ni asumas que representa toda la empresa si el dataset es de un canal."
            )

    for s in steps:
        lines.append(f"· {s.label}: {s.detail}")

    lines.append(f"Consulta ({plan.intent}):")
    if plan.intent == "forecast_revenue" and forecast is not None:
        for row in forecast.rows:
            kind = "histórico" if row.get("kind") == "historico" else "PROYECCIÓN"
            lines.append(f"  - [{kind}] {row.get('label')}: {row.get('value')}")
        lines.append(
            f"PROYECCIÓN PUNTO ({forecast.horizon_label}): {forecast.point_forecast} CLP"
        )
        lines.append(
            f"BANDA DE INCERTIDUMBRE: {forecast.low} – {forecast.high} CLP"
        )
        lines.append(f"MÉTODO: {forecast.method_label}")
        if forecast.mape_pct is not None:
            lines.append(f"ERROR HISTÓRICO (MAPE backtest 1 paso): {forecast.mape_pct}%")
        lines.append("SUPUESTOS:")
        for a in forecast.assumptions:
            lines.append(f"  · {a}")
        lines.append("LIMITACIONES:")
        for lim in forecast.limitations:
            lines.append(f"  · {lim}")
        lines.append(
            "En la respuesta: da primero el punto estimado + banda, declara el método en una frase, "
            "y deja claro que es proyección (no hecho). No presentes la proyección como certeza."
        )
    elif len(rows) <= 20:
        for row in rows:
            lines.append(f"  - {row.get('label')}: {row.get('value')}")
    else:
        for row in rows[:15]:
            lines.append(f"  - {row.get('label')}: {row.get('value')}")
        lines.append(f"  … y {len(rows) - 15} filas más")

    if plan.intent in ("total_revenue", "ticket_average", "units_sold") and rows:
        label = {
            "total_revenue": "TOTAL INGRESOS",
            "ticket_average": "TICKET PROMEDIO",
            "units_sold": "UNIDADES VENDIDAS",
        }[plan.intent]
        lines.append(f"{label}: {rows[0].get('value')}")
    if plan.intent in ("compare_quarters", "compare_halves") and len(rows) >= 2:
        a, b = rows[0], rows[1]
        try:
            va, vb = float(a.get("value") or 0), float(b.get("value") or 0)
            if va > 0:
                pct = (vb - va) / va * 100
                lines.append(
                    f"COMPARATIVO: {a.get('label')} {va:,.2f} → {b.get('label')} {vb:,.2f} "
                    f"({pct:+.1f}%). Usa EXACTAMENTE estos periodos y esta variación."
                )
                if abs(pct) >= 5:
                    severity = "relevante" if abs(pct) >= 15 else "moderada"
                    direction = "alza" if pct > 0 else "caída"
                    lines.append(
                        f"ANOMALÍA / SEÑAL ({severity}): {direction} de {abs(pct):.1f}% entre "
                        f"{a.get('label')} y {b.get('label')}. Puedes señalarla una vez al gerente "
                        "si aporta a la decisión; no satures."
                    )
        except (TypeError, ValueError):
            pass
    lines.append("Usa EXACTAMENTE estas cifras en tu respuesta gerencial.")
    return "\n".join(lines)


def _lazy_register_tabular(db: Session, category: str | None) -> None:
    from pathlib import Path

    from itplus.app.models.document import Document

    q = db.query(Document).filter(
        Document.status == "ready",
        Document.analyst_profile.is_(None),
    )
    if category and category.strip().lower() not in ("", "general"):
        q = q.filter(Document.category == category.strip().lower())

    for doc in q.all():
        suffix = Path(doc.storage_path).suffix.lower()
        if suffix in {".csv", ".xlsx", ".xlsm"}:
            register_document_dataset(db, doc)


def run_crisp_pipeline(
    db: Session,
    question: str,
    category: str | None = None,
    conversation_history: list[dict] | None = None,
) -> CrispPipelineResult:
    """Run full CRISP-DM pipeline when tabular datasets are available."""
    resolved = resolve_retrieval_question(question, conversation_history or [])
    steps: list[CrispStep] = [_business_step(question, resolved)]

    _lazy_register_tabular(db, category)
    candidates = list_ready_datasets(db, category)
    if not candidates:
        return CrispPipelineResult(success=False, steps=steps)

    selected = select_best_dataset(candidates, resolved)
    if not selected:
        return CrispPipelineResult(success=False, steps=steps)

    doc, profile = selected
    steps.append(profile_step(profile))
    steps.append(_prepare_step())

    plan = plan_query(profile, resolved)
    steps.append(_model_step(plan.intent))

    try:
        con = connect_dataset(doc.id)
        try:
            rows = execute_plan(con, plan)
        finally:
            con.close()
    except Exception as exc:
        logger.warning("CRISP SQL failed: %s", exc)
        steps.append(
            CrispStep(phase="evaluation", label="Evaluación", detail=f"Error SQL: {exc}")
        )
        return CrispPipelineResult(success=False, steps=steps)

    steps.append(_evaluate_step(rows))
    if not rows or all(r.get("value") in (None, 0) for r in rows):
        return CrispPipelineResult(success=False, steps=steps)

    forecast: ForecastResult | None = None
    if plan.intent == "forecast_revenue":
        forecast = build_revenue_forecast(rows)
        if forecast is None:
            steps.append(
                CrispStep(
                    phase="evaluation",
                    label="Evaluación",
                    detail="Serie mensual insuficiente (<3 meses) para proyectar",
                )
            )
            return CrispPipelineResult(success=False, steps=steps)
        rows = forecast.rows
        steps.append(
            CrispStep(
                phase="modeling",
                label="Proyección",
                detail=f"{forecast.method_label} → {forecast.horizon_label}",
            )
        )

    analytics = _build_analytics(plan, rows, doc.filename, forecast=forecast)
    llm_context = _build_llm_context(
        doc.filename,
        steps,
        plan,
        rows,
        profile=profile,
        question=resolved,
        forecast=forecast,
    )

    steps.append(
        CrispStep(
            phase="deployment",
            label="Despliegue",
            detail="Contexto analítico listo para narración gerencial",
        )
    )

    metrics: dict[str, Any] = {}
    if rows and plan.intent == "total_revenue" and len(rows) == 1:
        metrics["total_revenue"] = float(rows[0].get("value") or 0)

    return CrispPipelineResult(
        success=True,
        steps=steps,
        llm_context=llm_context,
        analytics=analytics,
        source_document_id=doc.id,
        source_document_name=doc.filename,
        metrics=metrics,
    )
