"""Parse PDF page vs Excel sheet from chunk metadata."""


def parse_document_location(metadata: dict) -> tuple[int | None, str | None]:
    """Return (page_number, sheet_name) from stored chunk metadata."""
    for key in ("page", "sheet"):
        raw = metadata.get(key)
        if raw is None:
            continue
        if isinstance(raw, int):
            return raw, None
        if isinstance(raw, str):
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.isdigit():
                return int(stripped), None
            return None, stripped
    return None, None


def format_document_location(page: int | None, sheet: str | None) -> str:
    if sheet:
        return f" (hoja {sheet})"
    if page is not None:
        return f" (página {page})"
    return ""
