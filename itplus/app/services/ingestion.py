"""Document parsing and chunking."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def parse_pdf(file_path: str) -> list[dict]:
    import fitz

    chunks_with_meta: list[dict] = []
    doc = fitz.open(file_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        for chunk_text in _split_text(text):
            chunks_with_meta.append({"content": chunk_text, "page": page_num + 1})
    doc.close()
    return chunks_with_meta


def parse_docx(file_path: str) -> list[dict]:
    from docx import Document as DocxDocument

    doc = DocxDocument(file_path)
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{"content": c, "page": None} for c in _split_text(full_text)]


def parse_txt(file_path: str) -> list[dict]:
    text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    return [{"content": c, "page": None} for c in _split_text(text)]


def parse_document(file_path: str, mime_type: str) -> list[dict]:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if mime_type == "application/pdf" or suffix == ".pdf":
        return parse_pdf(file_path)
    if mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ) or suffix in (".docx", ".doc"):
        return parse_docx(file_path)
    if mime_type.startswith("text/") or suffix in (".txt", ".md", ".csv"):
        return parse_txt(file_path)

    logger.warning("Unsupported mime type %s, attempting text read", mime_type)
    return parse_txt(file_path)
