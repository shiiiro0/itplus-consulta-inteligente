"""Parse vendor/meta rows from indexed CSV chunks without mixing notas into names."""

from __future__ import annotations

import re

_PAIR_PATTERN = re.compile(r"([a-zA-Z0-9_áéíóúñ]+):\s*([^|]+)")

_INVALID_VENDOR_MARKERS = (
    "notas",
    "seguimiento",
    "desempeño",
    "desempeno",
    "fuerte en",
    "sobre meta",
    "requiere",
    "mejor desempeño",
    "mejor desempeno",
)


def _parse_row_pairs(text: str) -> dict[str, str]:
    return {m.group(1).lower(): m.group(2).strip() for m in _PAIR_PATTERN.finditer(text)}


def _parse_float(value: str) -> float | None:
    try:
        return float(str(value).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def is_valid_vendor_name(name: str) -> bool:
    cleaned = name.strip()
    if not cleaned or len(cleaned) > 45:
        return False
    low = cleaned.lower()
    if low in {"vendedor", "notas", "region", "tanto"}:
        return False
    if any(marker in low for marker in _INVALID_VENDOR_MARKERS):
        return False
    if len(cleaned.split()) > 5:
        return False
    return True


def _row_from_pairs(pairs: dict[str, str]) -> dict[str, str] | None:
    vendor = pairs.get("vendedor", "").strip()
    if not vendor or not is_valid_vendor_name(vendor):
        return None
    if "cumplimiento_pct" not in pairs and "meta_q1_clp" not in pairs:
        return None
    return pairs


def _row_from_semicolon_line(line: str) -> dict[str, str] | None:
    if ";" not in line:
        return None
    parts = [p.strip() for p in line.split(";")]
    if len(parts) < 5:
        return None
    if parts[0].lower() in {"vendedor", "notas"}:
        return None
    vendor = parts[0]
    if not is_valid_vendor_name(vendor):
        return None
    if _parse_float(parts[3]) is None:
        return None
    row: dict[str, str] = {
        "vendedor": vendor,
        "meta_q1_clp": parts[1],
        "ventas_q1_clp": parts[2],
        "cumplimiento_pct": parts[3],
    }
    if len(parts) > 4:
        row["region"] = parts[4]
    if len(parts) > 5:
        row["notas"] = parts[5]
    return row


def parse_vendor_records(text: str) -> list[dict[str, str]]:
    """Extract vendor rows from pipe-indexed chunks or raw semicolon CSV lines."""
    looks_vendor = (
        "cumplimiento_pct" in text.lower()
        or "meta_q1_clp" in text.lower()
        or bool(re.search(r"^[A-Za-zÁ-ú].+;\d{6,};\d{6,};[\d.]+", text, re.M))
    )
    if not looks_vendor:
        return []

    records: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_row(row: dict[str, str] | None) -> None:
        if not row:
            return
        vendor = row.get("vendedor", "").strip()
        if not vendor or vendor in seen:
            return
        seen.add(vendor)
        records.append(row)

    for segment in re.split(r"(?=\s*vendedor:\s*)", text, flags=re.I):
        if not re.search(r"vendedor:\s*", segment, re.I):
            continue
        add_row(_row_from_pairs(_parse_row_pairs(segment)))

    for line in re.split(r"[\n\r]+", text):
        add_row(_row_from_semicolon_line(line.strip()))

    return records
