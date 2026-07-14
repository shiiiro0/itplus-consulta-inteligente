"""CRISP-DM Phase 4: Modeling — plan deterministic SQL from business intent."""

from __future__ import annotations

import re
from dataclasses import dataclass

from itplus.app.services.crisp_analyst.models import DatasetProfile

_MONTHS = {
    "enero": 1,
    "ene": 1,
    "febrero": 2,
    "feb": 2,
    "marzo": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "mayo": 5,
    "may": 5,
    "junio": 6,
    "jun": 6,
    "julio": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "septiembre": 9,
    "sep": 9,
    "octubre": 10,
    "oct": 10,
    "noviembre": 11,
    "nov": 11,
    "diciembre": 12,
    "dic": 12,
}


@dataclass
class QueryPlan:
    intent: str
    sql: str
    chart_type: str | None = None
    chart_title: str | None = None
    group_label: str | None = None


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _parse_year(question: str) -> int | None:
    m = re.search(r"\b(20\d{2})\b", question)
    return int(m.group(1)) if m else None


def _parse_month_range(question: str) -> tuple[int | None, int | None]:
    q = question.lower()
    found: list[int] = []
    for token, num in _MONTHS.items():
        if re.search(rf"\b{re.escape(token)}\b", q):
            found.append(num)
    if len(found) >= 2:
        return min(found), max(found)
    if len(found) == 1:
        return found[0], found[0]
    return None, None


def _date_filter_sql(profile: DatasetProfile, question: str) -> str:
    if not profile.date_column:
        return "1=1"

    clauses: list[str] = ["dt IS NOT NULL"]
    year = _parse_year(question)
    m_start, m_end = _parse_month_range(question)

    if year:
        clauses.append(f"EXTRACT(YEAR FROM dt) = {year}")

    if m_start and m_end:
        if m_start == m_end:
            clauses.append(f"EXTRACT(MONTH FROM dt) = {m_start}")
        else:
            clauses.append(f"EXTRACT(MONTH FROM dt) BETWEEN {m_start} AND {m_end}")

    q = question.lower()
    if "h1" in q or "primer semestre" in q or "1er semestre" in q:
        clauses.append("EXTRACT(MONTH FROM dt) BETWEEN 1 AND 6")
    elif "h2" in q or "segundo semestre" in q or "2do semestre" in q:
        clauses.append("EXTRACT(MONTH FROM dt) BETWEEN 7 AND 12")

    if "q1" in q:
        clauses.append("EXTRACT(MONTH FROM dt) BETWEEN 1 AND 3")
    elif "q2" in q:
        clauses.append("EXTRACT(MONTH FROM dt) BETWEEN 4 AND 6")
    elif "q3" in q:
        clauses.append("EXTRACT(MONTH FROM dt) BETWEEN 7 AND 9")
    elif "q4" in q:
        clauses.append("EXTRACT(MONTH FROM dt) BETWEEN 10 AND 12")

    if year is None and m_start is None:
        if profile.date_min and profile.date_max:
            clauses.append(f"dt >= DATE '{profile.date_min}' AND dt <= DATE '{profile.date_max}'")

    return " AND ".join(clauses)


def plan_query(profile: DatasetProfile, question: str) -> QueryPlan:
    q = question.lower()
    where = _date_filter_sql(profile, question)
    rev = profile.revenue_expression

    wants_chart = any(
        w in q
        for w in (
            "grafico",
            "gráfico",
            "chart",
            "visual",
            "muestrame",
            "muéstrame",
            "mostrar",
            "así",
            "asi",
            "pie",
            "torta",
            "linea",
            "línea",
        )
    )

    if profile.category_column and any(
        w in q for w in ("categoria", "categoría", "category", "familia", "segmento")
    ):
        col = _quote(profile.category_column)
        return QueryPlan(
            intent="by_category",
            sql=f"""
                SELECT {col} AS label, ROUND(SUM({rev}), 2) AS value
                FROM data_clean
                WHERE {where}
                GROUP BY 1
                ORDER BY value DESC
            """,
            chart_type="pie" if wants_chart else "bar",
            chart_title="Ingresos por categoría",
            group_label="Categoría",
        )

    if profile.city_column and any(
        w in q for w in ("ciudad", "city", "region", "región", "zona")
    ):
        col = _quote(profile.city_column)
        return QueryPlan(
            intent="by_city",
            sql=f"""
                SELECT {col} AS label, ROUND(SUM({rev}), 2) AS value
                FROM data_clean
                WHERE {where}
                GROUP BY 1
                ORDER BY value DESC
                LIMIT 15
            """,
            chart_type="bar",
            chart_title="Ingresos por ciudad",
            group_label="Ciudad",
        )

    if profile.date_column and any(
        w in q for w in ("mes", "mensual", "month", "tendencia", "evolución", "evolucion", "linea", "línea")
    ):
        return QueryPlan(
            intent="by_month",
            sql=f"""
                SELECT month_key AS label, ROUND(SUM({rev}), 2) AS value
                FROM data_clean
                WHERE {where} AND month_key IS NOT NULL
                GROUP BY 1
                ORDER BY 1
            """,
            chart_type="line" if wants_chart else "bar",
            chart_title="Ingresos por mes",
            group_label="Mes",
        )

    if any(w in q for w in ("compar", "versus", "vs", "h1", "h2", "semestre")):
        return QueryPlan(
            intent="compare_halves",
            sql=f"""
                SELECT
                    CASE WHEN EXTRACT(MONTH FROM dt) <= 6 THEN 'H1' ELSE 'H2' END AS label,
                    ROUND(SUM({rev}), 2) AS value
                FROM data_clean
                WHERE {where}
                GROUP BY 1
                ORDER BY 1
            """,
            chart_type="bar" if wants_chart else None,
            chart_title="Comparativo semestral",
            group_label="Periodo",
        )

    if profile.product_column and any(w in q for w in ("producto", "product", "top", "ranking")):
        col = _quote(profile.product_column)
        return QueryPlan(
            intent="top_products",
            sql=f"""
                SELECT {col} AS label, ROUND(SUM({rev}), 2) AS value
                FROM data_clean
                WHERE {where}
                GROUP BY 1
                ORDER BY value DESC
                LIMIT 10
            """,
            chart_type="bar",
            chart_title="Top productos por ingreso",
            group_label="Producto",
        )

    return QueryPlan(
        intent="total_revenue",
        sql=f"""
            SELECT 'total' AS label, ROUND(SUM({rev}), 2) AS value
            FROM data_clean
            WHERE {where}
        """,
        chart_type=None,
        chart_title="Total de ingresos",
    )
