"""Parse PDF page vs Excel sheet from chunk metadata."""

from itplus.app.schemas.chat_query import SourceCitation


def parse_document_location(metadata: dict) -> tuple[int | None, str | None]:
    """Return (page_number, sheet_name) from stored chunk metadata.

    "page" y "sheet" se procesan por separado y nunca se mezclan: antes, si
    "page" no estaba presente, se probaba "sheet" con la misma heurística de
    "¿son solo dígitos?" usada para páginas — así que un nombre de hoja de
    Excel puramente numérico (p. ej. una hoja llamada "2024" o "1") se
    devolvía como número de página en vez de nombre de hoja.
    """
    page_raw = metadata.get("page")
    if isinstance(page_raw, int):
        return page_raw, None
    if isinstance(page_raw, str) and page_raw.strip().isdigit():
        return int(page_raw.strip()), None

    sheet_raw = metadata.get("sheet")
    if isinstance(sheet_raw, str) and sheet_raw.strip():
        return None, sheet_raw.strip()

    return None, None


def format_document_location(page: int | None, sheet: str | None) -> str:
    if sheet:
        return f" (hoja {sheet})"
    if page is not None:
        return f" (página {page})"
    return ""


def build_context_from_hits(hits: list[dict], connector_note: str | None = None) -> str:
    """Junta los hits de retrieval en el bloque de contexto que se manda al
    LLM. RAGService y ConversationService tenían cada uno su propia copia
    idéntica de esta función (una con `connector_note`, otra sin él, pero
    con el mismo cuerpo) — se unifican aquí."""
    parts: list[str] = []
    if connector_note:
        parts.append(f"[Sistemas conectados]\n{connector_note}")
    for i, hit in enumerate(hits, 1):
        page, sheet = parse_document_location(hit)
        loc = format_document_location(page, sheet)
        parts.append(f"[Fuente {i}: {hit['document_name']}{loc}]\n{hit['content']}")
    return "\n\n---\n\n".join(parts)


def hits_to_source_citations(hits: list[dict]) -> list[SourceCitation]:
    """Convierte hits de retrieval (dicts con document_id/document_name/
    content/score) a SourceCitation. RAGService y ConversationService
    tenían cada uno su propia copia idéntica de este bloque."""
    sources: list[SourceCitation] = []
    for hit in hits:
        page, sheet = parse_document_location(hit)
        excerpt = hit["content"][:300] + ("..." if len(hit["content"]) > 300 else "")
        sources.append(
            SourceCitation(
                document_id=hit["document_id"],
                document_name=hit["document_name"],
                excerpt=excerpt,
                page=page,
                sheet=sheet,
                score=hit["score"],
            )
        )
    return sources
