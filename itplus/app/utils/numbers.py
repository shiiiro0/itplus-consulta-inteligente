"""Parsing helpers for numbers embedded in tabular document chunks.

Antes esta misma función (`_parse_float`) estaba duplicada de forma idéntica
en `document_analytics.py`, `vendor_rows.py` y `tabular_insights.py`, y en los
3 casos hacía `value.replace(",", ".")` — lo que funciona para "150,5" pero
rompe con el formato numérico chileno real de muchos CSV/XLSX exportados
desde Excel en `es-CL`, que usa `.` como separador de miles y `,` como
separador decimal (p. ej. "1.234.567,89"): el `replace` ciego deja
"1.234.567.89" (con 3 puntos), que `float()` no puede parsear, y la función
devolvía `None` silenciosamente para esas filas — perdiendo cifras reales sin
ningún error visible.
"""

from __future__ import annotations


def parse_localized_float(value: str | float | int | None) -> float | None:
    """Parsea un número que puede venir en formato `es-CL` (miles con `.`,
    decimales con `,`) o en formato "plano" con punto decimal (`1234.56`),
    que es lo que ya generan varias partes del pipeline (p. ej. precios
    unitarios calculados internamente).
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    has_comma = "," in s
    has_dot = "." in s

    try:
        if has_comma and has_dot:
            # El separador que aparece más a la derecha es el decimal; el
            # otro se trata como separador de miles y se descarta.
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif has_comma:
            # Solo coma(s): una sola coma es decimal (es-CL); más de una
            # coma solo puede ser separador de miles.
            s = s.replace(",", "") if s.count(",") > 1 else s.replace(",", ".")
        elif has_dot and s.count(".") > 1:
            # Más de un punto solo puede ser separador de miles
            # (ej. "1.234.567"); un solo punto se deja como decimal para no
            # romper el formato que ya usa el resto del pipeline.
            s = s.replace(".", "")
        return float(s)
    except (ValueError, TypeError):
        return None
