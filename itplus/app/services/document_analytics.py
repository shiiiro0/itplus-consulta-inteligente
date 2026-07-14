"""Phase 2 — structured analytics from tabular document chunks."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from itplus.app.connectors.base import ConnectorHit
from itplus.app.schemas.analytics import AnalyticsPayload, ChartDataset, ChartSpec, ComparisonSpec, TableSpec
from itplus.app.services.tabular_insights import build_tabular_summary
from itplus.app.services.vendor_rows import parse_vendor_records

_PAIR_PATTERN = re.compile(r"([a-zA-Z0-9_áéíóúñ]+):\s*([^|\n]+)")
_SALE_ROW_RE = re.compile(
    r"(20\d{2}-(?:0[1-9]|1[0-2]));([^;|]+);([^;|]+);([^;|]+);(\d+);(\d+)",
)
_VENDOR_ROW_RE = re.compile(
    r"^([A-Za-zÁ-ú][A-Za-zÁ-ú\s\.]+);(\d{6,});(\d{6,});([\d.]+);([^;|]+)",
    re.M,
)
_REGION_RE = re.compile(r"region:\s*([^|]+)\s*\|\s*ventas_q1_clp:\s*(\d+)", re.I)

_ANALYTICS_HINTS = (
    "compar", "vs", "versus", "variación", "variacion", "tendencia", "evolución", "evolucion",
    "cuanto", "cuánto", "cuantos", "cuántos", "total", "porcentaje", "%", "meta", "metas",
    "vendedor", "ventas", "vendimos", "vendió", "quiebre", "quiebres", "2024", "2025", "2026",
    "trimestre", "q1", "q2", "mes", "gráfico", "grafico", "distribución", "distribucion",
    "ingreso", "factur", "pedido", "categor", "ciudad", "producto",
)

_FOLLOWUP_CHART_RE = re.compile(
    r"muestr|gr[aá]fic|desglose|visual|detalle|torta|tabla|\bas[ií]\b|\bok\b",
    re.I,
)

_ECOMMERCE_ROW_RE = re.compile(
    r"ORD\d+,([^,]+),([^,]+),(\d+),([\d.]+),([^,]+),(20\d{2}-\d{2}-\d{2})",
)

_MONTH_LABELS = {
    "01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr", "05": "May", "06": "Jun",
    "07": "Jul", "08": "Ago", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic",
}


def is_chart_followup(question: str) -> bool:
    return bool(_FOLLOWUP_CHART_RE.search((question or "").strip()))


def wants_analytics(question: str) -> bool:
    q = question.lower()
    if any(h in q for h in _ANALYTICS_HINTS):
        return True
    return is_chart_followup(question)


def resolve_retrieval_question(
    question: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Expand short follow-ups (e.g. 'muéstramelo') with the prior user question."""
    q = (question or "").strip()
    if not history:
        return q

    q_lower = q.lower()
    needs_prior = is_chart_followup(q) or (
        len(q) < 45 and not any(h in q_lower for h in _ANALYTICS_HINTS)
    )
    if not needs_prior:
        return q

    for turn in reversed(history):
        if turn.get("role") != "user":
            continue
        prior = (turn.get("content") or "").strip()
        if len(prior) < 12:
            continue
        prior_lower = prior.lower()
        if any(h in prior_lower for h in _ANALYTICS_HINTS) or "vend" in prior_lower:
            return f"{prior} — {q}"
    return q


def _parse_row_pairs(text: str) -> dict[str, str]:
    return {m.group(1).lower(): m.group(2).strip() for m in _PAIR_PATTERN.finditer(text)}


def _parse_float(value: str) -> float | None:
    try:
        return float(str(value).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def _format_clp_short(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}".replace(",", ".")


def _format_clp(value: float) -> str:
    return f"${value:,.0f} CLP".replace(",", ".")


def _month_label(ym: str) -> str:
    parts = ym.split("-")
    if len(parts) == 2:
        return f"{_MONTH_LABELS.get(parts[1], parts[1])} {parts[0]}"
    return ym


@dataclass
class ParsedRows:
    sales: list[dict[str, str]] = field(default_factory=list)
    vendor_meta: list[dict[str, str]] = field(default_factory=list)
    quiebres: list[dict[str, str]] = field(default_factory=list)
    financial_q1: list[dict[str, str]] = field(default_factory=list)
    region_sales: list[dict[str, str]] = field(default_factory=list)


def _parse_ecommerce_csv_blob(text: str) -> list[dict[str, str]]:
    """Parse ecommerce CSV rows: Order_ID,Product,Category,Quantity,Price,City,Date."""
    rows: list[dict[str, str]] = []
    for m in _ECOMMERCE_ROW_RE.finditer(text):
        qty = int(m.group(3))
        unit_price = _parse_float(m.group(4)) or 0.0
        date = m.group(6)
        rows.append({
            "mes": date[:7],
            "vendedor": m.group(5).strip(),
            "producto": m.group(1).strip(),
            "familia": m.group(2).strip(),
            "unidades": str(qty),
            "monto_clp": str(unit_price * qty),
        })
    return rows


def _parse_sales_csv_blob(text: str) -> list[dict[str, str]]:
    if "monto_clp" not in text.lower():
        return []
    rows: list[dict[str, str]] = []
    for m in _SALE_ROW_RE.finditer(text):
        rows.append({
            "mes": m.group(1),
            "vendedor": m.group(2).strip(),
            "producto": m.group(3).strip(),
            "familia": m.group(4).strip(),
            "unidades": m.group(5),
            "monto_clp": m.group(6),
        })
    return rows


def _parse_vendor_csv_blob(text: str) -> list[dict[str, str]]:
    return parse_vendor_records(text)


def _parse_financial_blocks(text: str) -> list[dict[str, str]]:
    if "total_q1" not in text.lower():
        return []
    blocks: list[dict[str, str]] = []
    for segment in re.split(r"(?=concepto:\s*)", text, flags=re.I):
        pairs = _parse_row_pairs(segment)
        concepto = pairs.get("concepto", "").lower()
        if pairs.get("total_q1") and ("ingreso" in concepto or "venta" in concepto):
            blocks.append(pairs)
    return blocks


def _parse_region_sales(text: str) -> list[dict[str, str]]:
    return [
        {"region": m.group(1).strip(), "ventas_q1_clp": m.group(2)}
        for m in _REGION_RE.finditer(text)
    ]


def _parse_quiebre_blob(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for tipo in re.findall(r"Quiebre\s+(SAP|WMS)", text, re.I):
        rows.append({"tipo_quiebre": f"Quiebre {tipo.upper()}"})
    return rows


def _extract_rows(hits: list[ConnectorHit]) -> ParsedRows:
    parsed = ParsedRows()
    seen_sales: set[str] = set()
    seen_vendors: set[str] = set()

    for hit in hits:
        content = hit.content

        for row in _parse_ecommerce_csv_blob(content):
            key = f"{row.get('mes')}|{row.get('producto')}|{row.get('monto_clp')}"
            if key not in seen_sales:
                seen_sales.add(key)
                parsed.sales.append(row)

        for row in _parse_sales_csv_blob(content):
            key = f"{row.get('mes')}|{row.get('vendedor')}|{row.get('monto_clp')}"
            if key not in seen_sales:
                seen_sales.add(key)
                parsed.sales.append(row)

        for row in parse_vendor_records(content):
            key = row.get("vendedor", "")
            if key and key not in seen_vendors:
                seen_vendors.add(key)
                parsed.vendor_meta.append(row)

        for block in _parse_financial_blocks(content):
            parsed.financial_q1.append(block)

        for row in _parse_region_sales(content):
            parsed.region_sales.append(row)

        for row in _parse_quiebre_blob(content):
            parsed.quiebres.append(row)

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            pairs = _parse_row_pairs(line)
            if not pairs:
                continue

            if "mes" in pairs and "monto_clp" in pairs:
                key = f"{pairs.get('mes')}|{pairs.get('monto_clp')}"
                if key not in seen_sales:
                    seen_sales.add(key)
                    parsed.sales.append(pairs)
            elif "tipo_quiebre" in pairs or ("cliente" in pairs and "oc" in pairs):
                parsed.quiebres.append(pairs)

    return parsed


def _sum_sales(rows: list[dict[str, str]], year: str | None = None, months: set[str] | None = None) -> float:
    total = 0.0
    for row in rows:
        mes = row.get("mes", "")
        if year and not mes.startswith(f"{year}-"):
            continue
        if months and mes.split("-")[-1] not in months:
            continue
        amount = _parse_float(row.get("monto_clp", ""))
        if amount is not None:
            total += amount
    return total


def _sales_by_month(rows: list[dict[str, str]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        mes = row.get("mes", "")
        amount = _parse_float(row.get("monto_clp", ""))
        if mes and amount is not None:
            totals[mes] += amount
    return dict(totals)


def _sales_by_vendedor(rows: list[dict[str, str]], year: str | None = None) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        mes = row.get("mes", "")
        if year and not mes.startswith(f"{year}-"):
            continue
        vendor = row.get("vendedor", "").strip()
        amount = _parse_float(row.get("monto_clp", ""))
        if vendor and amount is not None:
            totals[vendor] += amount
    return dict(totals)


def _detect_years(rows: list[dict[str, str]]) -> list[str]:
    years: set[str] = set()
    for row in rows:
        mes = row.get("mes", "")
        if len(mes) >= 4:
            years.add(mes[:4])
    return sorted(years)


def _build_yoy_comparisons(sales: list[dict[str, str]], question: str) -> tuple[list[ComparisonSpec], list[ChartSpec], list[TableSpec]]:
    comparisons: list[ComparisonSpec] = []
    charts: list[ChartSpec] = []
    tables: list[TableSpec] = []

    years = _detect_years(sales)
    if len(years) < 2:
        return comparisons, charts, tables

    q = question.lower()
    q1_months = {"01", "02", "03"}
    focus_q1 = any(w in q for w in ("q1", "ene", "enero", "marzo", "trimestre", "ene-mar", "ene–mar"))

    year_a, year_b = years[-2], years[-1]
    if focus_q1 or "compar" in q or "vs" in q:
        total_a = _sum_sales(sales, year_a, q1_months)
        total_b = _sum_sales(sales, year_b, q1_months)
        if total_a > 0 and total_b > 0:
            change = (total_b - total_a) / total_a * 100
            comparisons.append(
                ComparisonSpec(
                    label="Ventas Q1 (ene–mar)",
                    period_a=str(year_a),
                    period_b=str(year_b),
                    value_a=total_a,
                    value_b=total_b,
                    change_pct=round(change, 1),
                    unit="clp",
                )
            )
            charts.append(
                ChartSpec(
                    id="sales_yoy_pie",
                    chart_type="pie",
                    title=f"Ventas Q1 — {year_a} vs {year_b}",
                    labels=[str(year_a), str(year_b)],
                    datasets=[ChartDataset(label="Ventas Q1", values=[total_a, total_b])],
                    value_format="clp",
                )
            )

        by_month_a = {m: v for m, v in _sales_by_month(sales).items() if m.startswith(f"{year_a}-") and m.split("-")[1] in q1_months}
        by_month_b = {m: v for m, v in _sales_by_month(sales).items() if m.startswith(f"{year_b}-") and m.split("-")[1] in q1_months}
        month_nums = sorted(set(
            [m.split("-")[1] for m in by_month_a] + [m.split("-")[1] for m in by_month_b]
        ))

        if month_nums:
            labels = [_MONTH_LABELS.get(m, m) for m in month_nums]
            values_a = [by_month_a.get(f"{year_a}-{m}", 0) for m in month_nums]
            values_b = [by_month_b.get(f"{year_b}-{m}", 0) for m in month_nums]
            charts.append(
                ChartSpec(
                    id="sales_yoy_bar",
                    chart_type="bar",
                    title=f"Ventas mensuales Q1 — {year_a} vs {year_b}",
                    labels=labels,
                    datasets=[
                        ChartDataset(label=str(year_a), values=values_a),
                        ChartDataset(label=str(year_b), values=values_b),
                    ],
                    value_format="clp",
                )
            )
            charts.append(
                ChartSpec(
                    id="sales_yoy_line",
                    chart_type="line",
                    title=f"Tendencia mensual Q1 — {year_a} vs {year_b}",
                    labels=labels,
                    datasets=[
                        ChartDataset(label=str(year_a), values=values_a),
                        ChartDataset(label=str(year_b), values=values_b),
                    ],
                    value_format="clp",
                    optional=True,
                )
            )

            table_rows = []
            for m in month_nums:
                va = by_month_a.get(f"{year_a}-{m}", 0)
                vb = by_month_b.get(f"{year_b}-{m}", 0)
                chg = ((vb - va) / va * 100) if va > 0 else 0
                table_rows.append([
                    _MONTH_LABELS.get(m, m),
                    _format_clp_short(va),
                    _format_clp_short(vb),
                    f"{chg:+.1f}%",
                ])
            tables.append(
                TableSpec(
                    id="sales_yoy_table",
                    title=f"Comparativo mensual Q1 ({year_a} vs {year_b})",
                    columns=["Mes", str(year_a), str(year_b), "Variación"],
                    rows=table_rows,
                )
            )

    if "vendedor" in q and len(years) >= 2:
        vend_a = _sales_by_vendedor(sales, year_a)
        vend_b = _sales_by_vendedor(sales, year_b)
        all_vendors = sorted(set(vend_a) | set(vend_b))
        if all_vendors:
            charts.append(
                ChartSpec(
                    id="sales_by_vendor",
                    chart_type="bar",
                    title=f"Ventas por vendedor — {year_b}",
                    labels=all_vendors,
                    datasets=[ChartDataset(label=str(year_b), values=[vend_b.get(v, 0) for v in all_vendors])],
                    value_format="clp",
                )
            )

    return comparisons, charts, tables


def _build_vendor_analytics(vendor_meta: list[dict[str, str]]) -> tuple[list[ChartSpec], list[TableSpec], list[ComparisonSpec]]:
    charts: list[ChartSpec] = []
    tables: list[TableSpec] = []
    comparisons: list[ComparisonSpec] = []

    ranked: list[tuple[str, float, dict[str, str]]] = []
    for row in vendor_meta:
        vendor = row.get("vendedor", "").strip()
        pct = _parse_float(row.get("cumplimiento_pct", ""))
        if vendor and pct is not None:
            ranked.append((vendor, pct, row))
    ranked.sort(key=lambda x: x[1], reverse=True)

    if not ranked:
        return charts, tables, comparisons

    vendors = [r[0] for r in ranked]
    pcts = [r[1] for r in ranked]

    charts.append(
        ChartSpec(
            id="vendor_compliance",
            chart_type="bar",
            title="Cumplimiento de meta Q1 por vendedor",
            labels=vendors,
            datasets=[ChartDataset(label="Cumplimiento %", values=pcts)],
            value_format="pct",
        )
    )

    table_rows = []
    for vendor, pct, row in ranked:
        meta = _parse_float(row.get("meta_q1_clp", ""))
        ventas = _parse_float(row.get("ventas_q1_clp", ""))
        table_rows.append([
            vendor,
            _format_clp_short(meta) if meta else "—",
            _format_clp_short(ventas) if ventas else "—",
            f"{pct:.1f}%",
            row.get("region", "—"),
            row.get("notas", "—"),
        ])

    tables.append(
        TableSpec(
            id="vendor_meta_table",
            title="Metas y ventas Q1 por vendedor",
            columns=["Vendedor", "Meta Q1", "Ventas Q1", "Cumplimiento", "Región", "Notas"],
            rows=table_rows,
        )
    )

    best = ranked[0]
    comparisons.append(
        ComparisonSpec(
            label=f"Mejor cumplimiento — {best[0]}",
            period_a="Meta Q1",
            period_b="Ventas Q1",
            value_a=_parse_float(best[2].get("meta_q1_clp", "")) or 0,
            value_b=_parse_float(best[2].get("ventas_q1_clp", "")) or 0,
            change_pct=best[1],
            unit="clp",
        )
    )

    return charts, tables, comparisons


def _build_quiebre_analytics(quiebres: list[dict[str, str]]) -> tuple[list[ChartSpec], list[TableSpec]]:
    charts: list[ChartSpec] = []
    tables: list[TableSpec] = []

    tipo_counter: Counter[str] = Counter()
    familia_counter: Counter[str] = Counter()
    for row in quiebres:
        tipo = row.get("tipo_quiebre", "").strip()
        familia = row.get("familia", "").strip()
        if tipo:
            tipo_counter[tipo] += 1
        if familia:
            familia_counter[familia] += 1

    if tipo_counter:
        labels = list(tipo_counter.keys())
        values = [float(tipo_counter[k]) for k in labels]
        charts.append(
            ChartSpec(
                id="quiebres_by_type",
                chart_type="pie",
                title="Quiebres por tipo",
                labels=labels,
                datasets=[ChartDataset(label="Cantidad", values=values)],
                value_format="number",
            )
        )
        total = sum(tipo_counter.values())
        table_rows = [
            [tipo, str(count), f"{count / total * 100:.1f}%"]
            for tipo, count in tipo_counter.most_common()
        ]
        tables.append(
            TableSpec(
                id="quiebres_type_table",
                title="Detalle de quiebres por tipo",
                columns=["Tipo", "Cantidad", "% del total"],
                rows=table_rows,
            )
        )

    if familia_counter and len(familia_counter) > 1:
        charts.append(
            ChartSpec(
                id="quiebres_by_family",
                chart_type="bar",
                title="Quiebres por familia de producto",
                labels=list(familia_counter.keys()),
                datasets=[ChartDataset(label="Cantidad", values=[float(familia_counter[k]) for k in familia_counter])],
                value_format="number",
            )
        )

    return charts, tables


def _build_financial_q1_analytics(
    financial: list[dict[str, str]],
    region_sales: list[dict[str, str]],
    question: str,
) -> tuple[list[ComparisonSpec], list[ChartSpec], list[TableSpec]]:
    comparisons: list[ComparisonSpec] = []
    charts: list[ChartSpec] = []
    tables: list[TableSpec] = []

    for block in financial:
        total = _parse_float(block.get("total_q1", ""))
        var_pct = _parse_float(block.get("var_vs_2025_pct", ""))
        enero = _parse_float(block.get("enero", ""))
        febrero = _parse_float(block.get("febrero", ""))
        marzo = _parse_float(block.get("marzo", ""))

        if total and var_pct is not None:
            total_2025 = total / (1 + var_pct / 100) if var_pct != -100 else 0
            comparisons.append(
                ComparisonSpec(
                    label="Ventas Q1 (ene–mar)",
                    period_a="2025",
                    period_b="2026",
                    value_a=round(total_2025),
                    value_b=round(total),
                    change_pct=round(var_pct, 1),
                    unit="clp",
                )
            )

        if enero and febrero and marzo:
            charts.append(
                ChartSpec(
                    id="sales_q1_monthly_2026",
                    chart_type="pie",
                    title="Distribución ventas Q1 2026 por mes",
                    labels=["Ene", "Feb", "Mar"],
                    datasets=[ChartDataset(label="2026", values=[enero, febrero, marzo])],
                    value_format="clp",
                )
            )
            table_rows = [
                ["Enero", _format_clp_short(enero), "—", "—"],
                ["Febrero", _format_clp_short(febrero), "—", "—"],
                ["Marzo", _format_clp_short(marzo), "—", "—"],
                ["Total Q1", _format_clp_short(total or (enero + febrero + marzo)), "—", f"{var_pct:+.1f}%" if var_pct else "—"],
            ]
            if var_pct is not None and total:
                total_2025 = total / (1 + var_pct / 100)
                table_rows[3][2] = _format_clp_short(total_2025)
            tables.append(
                TableSpec(
                    id="financial_q1_table",
                    title="Resumen ventas Q1 2026",
                    columns=["Mes", "2026", "2025 (est.)", "Variación"],
                    rows=table_rows,
                )
            )

    if region_sales:
        labels = [r["region"] for r in region_sales]
        values = [_parse_float(r["ventas_q1_clp"]) or 0 for r in region_sales]
        if labels and any(values):
            charts.append(
                ChartSpec(
                    id="sales_by_region",
                    chart_type="bar",
                    title="Ventas Q1 por región",
                    labels=labels,
                    datasets=[ChartDataset(label="Ventas Q1", values=values)],
                    value_format="clp",
                )
            )

    return comparisons, charts, tables


_CHART_PRIORITY = {"pie": 0, "bar": 1, "line": 2}


def _trim_analytics_payload(payload: AnalyticsPayload) -> AnalyticsPayload:
    """Mantener torta + barra como base; líneas solo como opcionales."""
    primary = [c for c in payload.charts if not c.optional]
    optional = [c for c in payload.charts if c.optional]

    pies = [c for c in primary if c.chart_type == "pie"][:1]
    bars = [c for c in primary if c.chart_type == "bar"][:1]
    other_primary = [c for c in primary if c.chart_type not in ("pie", "bar")][:1]

    trimmed_charts = pies + bars + other_primary + optional[:2]
    trimmed_tables = payload.tables[:1]

    return AnalyticsPayload(
        charts=trimmed_charts,
        tables=trimmed_tables,
        comparisons=payload.comparisons,
    )


def build_analytics(hits: list[ConnectorHit], question: str) -> AnalyticsPayload | None:
    """Build structured charts/tables/comparisons from document hits."""
    if not hits or not wants_analytics(question):
        return None

    rows = _extract_rows(hits)
    q = question.lower()

    payload = AnalyticsPayload()
    seen_chart_ids: set[str] = set()
    seen_table_ids: set[str] = set()

    def add_charts(charts: list[ChartSpec]) -> None:
        for c in charts:
            if c.id not in seen_chart_ids:
                payload.charts.append(c)
                seen_chart_ids.add(c.id)

    def add_tables(tables: list[TableSpec]) -> None:
        for t in tables:
            if t.id not in seen_table_ids:
                payload.tables.append(t)
                seen_table_ids.add(t.id)

    if rows.sales and any(w in q for w in ("compar", "vs", "ventas", "2025", "2026", "ene", "mar", "trimestre", "q1")):
        comps, charts, tables = _build_yoy_comparisons(rows.sales, question)
        payload.comparisons.extend(comps)
        add_charts(charts)
        add_tables(tables)

    if rows.financial_q1 and any(w in q for w in ("compar", "vs", "ventas", "2025", "2026", "ene", "mar", "trimestre", "q1")):
        comps, charts, tables = _build_financial_q1_analytics(rows.financial_q1, rows.region_sales, question)
        if not payload.comparisons:
            payload.comparisons.extend(comps)
        add_charts(charts)
        add_tables(tables)

    if rows.vendor_meta and any(w in q for w in ("vendedor", "meta", "cumpli", "q1", "trimestre", "mejor", "quien", "quién")):
        charts, tables, comps = _build_vendor_analytics(rows.vendor_meta)
        add_charts(charts)
        add_tables(tables)
        payload.comparisons.extend(comps)

    if rows.quiebres and any(w in q for w in ("quiebre", "tipo", "familia", "cliente")):
        charts, tables = _build_quiebre_analytics(rows.quiebres)
        add_charts(charts)
        add_tables(tables)

    if not payload.charts and not payload.tables and not payload.comparisons:
        if rows.sales:
            by_month = _sales_by_month(rows.sales)
            if by_month:
                sorted_months = sorted(by_month.keys())
                add_charts([
                    ChartSpec(
                        id="sales_trend",
                        chart_type="line",
                        title="Evolución de ventas por mes",
                        labels=[_month_label(m) for m in sorted_months],
                        datasets=[ChartDataset(label="Ventas", values=[by_month[m] for m in sorted_months])],
                        value_format="clp",
                    )
                ])
            by_category: dict[str, float] = defaultdict(float)
            for row in rows.sales:
                cat = row.get("familia", "").strip() or "Sin categoría"
                amount = _parse_float(row.get("monto_clp", ""))
                if amount is not None:
                    by_category[cat] += amount
            if by_category:
                labels = sorted(by_category.keys(), key=lambda k: by_category[k], reverse=True)[:6]
                add_charts([
                    ChartSpec(
                        id="sales_by_category",
                        chart_type="pie",
                        title="Ventas por categoría",
                        labels=labels,
                        datasets=[ChartDataset(label="Ventas", values=[by_category[l] for l in labels])],
                        value_format="clp",
                    )
                ])
        if rows.vendor_meta:
            charts, tables, comps = _build_vendor_analytics(rows.vendor_meta)
            add_charts(charts)
            add_tables(tables)
            payload.comparisons.extend(comps)
        if rows.quiebres:
            charts, tables = _build_quiebre_analytics(rows.quiebres)
            add_charts(charts)
            add_tables(tables)

    if not payload.charts and not payload.tables and not payload.comparisons:
        return None

    return _trim_analytics_payload(payload)


def build_analytics_context(payload: AnalyticsPayload | None, hits: list[ConnectorHit], question: str) -> str:
    """Text block for LLM: tabular summary + pre-calculated comparison figures."""
    parts: list[str] = []

    tabular = build_tabular_summary(hits, question)
    if tabular:
        parts.append(tabular)

    if not payload:
        return "\n\n".join(parts)

    if payload.comparisons:
        parts.append("COMPARATIVOS CALCULADOS (usar estas cifras exactas en la respuesta):")
        for c in payload.comparisons:
            if c.unit == "clp" and c.label != f"Mejor cumplimiento — {c.label.split(' — ')[-1] if ' — ' in c.label else c.label}":
                parts.append(
                    f"  • {c.label}: {c.period_a} {_format_clp(c.value_a)} → "
                    f"{c.period_b} {_format_clp(c.value_b)} ({c.change_pct:+.1f}%)"
                )
            elif "Mejor cumplimiento" in c.label:
                parts.append(f"  • {c.label}: cumplimiento {c.change_pct:.1f}%")
            else:
                parts.append(
                    f"  • {c.label}: {c.period_a} → {c.period_b}, variación {c.change_pct:+.1f}%"
                )

    parts.append(
        "Nota: responde de forma contundente al inicio y desarrolla en 3–4 párrafos con interpretación. "
        "La tarjeta comparativa se muestra aparte; los gráficos solo si el gerente lo pide."
    )

    return "\n\n".join(parts)
