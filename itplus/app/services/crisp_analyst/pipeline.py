"""CRISP-DM orchestrator: business → data → prepare → model → evaluate → deploy."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from itplus.app.schemas.analytics import AnalyticsPayload, ChartDataset, ChartSpec, TableSpec
from itplus.app.services.crisp_analyst.executor import execute_plan
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
        "by_category": "Desglose por categoría",
        "by_city": "Desglose por ciudad",
        "by_month": "Serie mensual",
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


def _build_analytics(plan, rows: list[dict[str, Any]], doc_name: str) -> AnalyticsPayload | None:
    if not rows:
        return None

    if plan.intent == "total_revenue" and len(rows) == 1:
        val = float(rows[0].get("value") or 0)
        return AnalyticsPayload(
            tables=[
                TableSpec(
                    id="crisp_total",
                    title=f"Ingresos totales — {doc_name}",
                    columns=["Métrica", "Valor (CLP)"],
                    rows=[["Ingresos totales", f"${val:,.0f}"]],
                )
            ],
        )

    labels = [str(r.get("label", "")) for r in rows]
    values = [float(r.get("value") or 0) for r in rows]

    charts: list[ChartSpec] = []
    if plan.chart_type and labels:
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

    top = max(rows, key=lambda r: float(r.get("value") or 0))
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

    if not charts and not tables:
        return None

    return AnalyticsPayload(charts=charts, tables=tables)


def _build_llm_context(
    doc_name: str,
    steps: list[CrispStep],
    plan,
    rows: list[dict[str, Any]],
) -> str:
    lines = [
        "=== Análisis CRISP-DM (DuckDB — no inventar cifras) ===",
        f"Dataset: {doc_name}",
    ]
    for s in steps:
        lines.append(f"· {s.label}: {s.detail}")

    lines.append(f"Consulta ({plan.intent}):")
    if len(rows) <= 20:
        for row in rows:
            lines.append(f"  - {row.get('label')}: {row.get('value')}")
    else:
        for row in rows[:15]:
            lines.append(f"  - {row.get('label')}: {row.get('value')}")
        lines.append(f"  … y {len(rows) - 15} filas más")

    if plan.intent == "total_revenue" and rows:
        lines.append(f"TOTAL INGRESOS: {rows[0].get('value')}")
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

    analytics = _build_analytics(plan, rows, doc.filename)
    llm_context = _build_llm_context(doc.filename, steps, plan, rows)

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
