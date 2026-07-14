"""Lightweight pre-aggregation for tabular document chunks (manager-friendly context)."""

from __future__ import annotations

import re
from collections import Counter

from itplus.app.connectors.base import ConnectorHit
from itplus.app.services.vendor_rows import parse_vendor_records

_COUNT_HINTS = (
    "cuanto", "cuánto", "cuantos", "cuántos", "cantidad", "total", "conteo",
    "por tipo", "por categor", "cuántas", "cuantas", "distribución", "distribucion",
    "compar", "porcentaje", "%", "cuánto hay", "cuanto hay",
)

_VENDOR_HINTS = (
    "vendedor", "vendedores", "meta", "metas", "cumpli", "q1", "trimestre",
    "quien", "quién", "mejor", "peor", "equipo comercial", "ventas",
)

_FIELD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("tipo_quiebre", re.compile(r"tipo_quiebre:\s*([^|\n;]+)", re.I)),
    ("cliente", re.compile(r"cliente:\s*([^|\n;]+)", re.I)),
    ("familia", re.compile(r"familia:\s*([^|\n;]+)", re.I)),
    ("origen", re.compile(r"origen:\s*([^|\n;]+)", re.I)),
    ("quiebre", re.compile(r"Quiebre\s+(SAP|WMS)", re.I)),
]

_PAIR_PATTERN = re.compile(r"([a-zA-Z0-9_]+):\s*([^|\n;]+)")


def _question_wants_aggregation(question: str) -> bool:
    q = question.lower()
    return any(h in q for h in _COUNT_HINTS) or any(h in q for h in _VENDOR_HINTS)


def _infer_focus_field(question: str) -> str | None:
    q = question.lower()
    if "vendedor" in q or "meta" in q or "cumpli" in q:
        return "vendedor"
    if "tipo" in q or "quiebre" in q:
        return "tipo_quiebre"
    if "cliente" in q:
        return "cliente"
    if "familia" in q or "producto" in q:
        return "familia"
    if "origen" in q:
        return "origen"
    return None


def _parse_row_pairs(text: str) -> dict[str, str]:
    return {m.group(1).lower(): m.group(2).strip() for m in _PAIR_PATTERN.finditer(text)}


def _parse_float(value: str) -> float | None:
    try:
        return float(value.replace(",", ".").strip())
    except ValueError:
        return None


def _format_clp(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f} millones CLP"
    return f"${value:,.0f} CLP".replace(",", ".")


def _build_vendor_summary(hits: list[ConnectorHit], question: str) -> str:
    """Extract vendedor rows from structured CSV chunks."""
    meta_rows: list[dict[str, str]] = []
    all_vendors: set[str] = set()

    for hit in hits:
        for row in parse_vendor_records(hit.content):
            vendor = row.get("vendedor", "").strip()
            if vendor:
                all_vendors.add(vendor)
                meta_rows.append(row)

    q = question.lower()
    lines: list[str] = []

    if meta_rows:
        ranked: list[tuple[str, float, dict[str, str]]] = []
        for row in meta_rows:
            vendor = row.get("vendedor", "").strip()
            pct = _parse_float(row.get("cumplimiento_pct", ""))
            if vendor and pct is not None:
                ranked.append((vendor, pct, row))
        ranked.sort(key=lambda x: x[1], reverse=True)

        if ranked:
            lines.append(
                "RESUMEN DE VENDEDORES Y METAS (extraído de los datos — usar SOLO estos nombres y cifras):"
            )
            for vendor, pct, row in ranked:
                meta = _parse_float(row.get("meta_q1_clp", ""))
                ventas = _parse_float(row.get("ventas_q1_clp", ""))
                detail = f"  • {vendor}: cumplimiento {pct:.1f}%"
                if meta is not None:
                    detail += f", meta Q1 {_format_clp(meta)}"
                if ventas is not None:
                    detail += f", ventas Q1 {_format_clp(ventas)}"
                if row.get("notas"):
                    detail += f" ({row['notas']})"
                lines.append(detail)
            best = ranked[0]
            lines.append(
                f"Mejor cumplimiento Q1 en estos datos: {best[0]} con {best[1]:.1f}%."
            )

    if all_vendors and any(w in q for w in ("cuantos", "cuántos", "cuantas", "cuántas", "total", "hay")):
        sorted_vendors = sorted(all_vendors)
        lines.append(
            f"Vendedores distintos encontrados en los fragmentos analizados ({len(sorted_vendors)}): "
            + ", ".join(sorted_vendors)
        )

    return "\n".join(lines)


def build_tabular_summary(hits: list[ConnectorHit], question: str) -> str:
    """Build a numeric summary block for the LLM when the question is analytical."""
    if not hits or not _question_wants_aggregation(question):
        return ""

    vendor_summary = _build_vendor_summary(hits, question)
    if vendor_summary and _infer_focus_field(question) == "vendedor":
        return vendor_summary

    focus = _infer_focus_field(question)
    counters: dict[str, Counter[str]] = {name: Counter() for name, _ in _FIELD_PATTERNS}

    for hit in hits:
        text = hit.content
        for field_name, pattern in _FIELD_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(1).strip()
                if not value or value in ("", "None", "null"):
                    continue
                if field_name == "quiebre":
                    value = f"Quiebre {value.upper()}"
                counters[field_name][value] += 1

    primary = focus if focus and focus != "vendedor" and counters.get(focus) else None
    if primary == "tipo_quiebre" and not counters.get("tipo_quiebre") and counters.get("quiebre"):
        primary = "quiebre"
    if primary is None:
        for name, counter in counters.items():
            if counter:
                primary = name
                break

    counter_summary = ""
    if primary:
        counter = counters[primary]
        total = sum(counter.values())
        if total > 0:
            label_map = {
                "tipo_quiebre": "tipo de quiebre",
                "quiebre": "tipo de quiebre",
                "cliente": "cliente",
                "familia": "familia de producto",
                "origen": "origen",
            }
            field_label = label_map.get(primary, primary)
            lines = [
                "RESUMEN NUMÉRICO (extraído de los documentos, usar estos números en la respuesta):",
                f"Desglose por {field_label} (total {total} registros en los fragmentos analizados):",
            ]
            for value, count in counter.most_common(15):
                pct = count / total * 100
                lines.append(f"  • {value}: {count} ({pct:.1f}%)")
            counter_summary = "\n".join(lines)

    parts = [p for p in (vendor_summary, counter_summary) if p]
    return "\n\n".join(parts)
