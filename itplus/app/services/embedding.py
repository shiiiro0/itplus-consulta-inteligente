"""Embedding service using sentence-transformers (local, no API key needed)."""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from itplus.app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    logger.info("Loading embedding model: %s", settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def embed_text(self, text: str) -> list[float]:
        model = _get_model()
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = _get_model()
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [e.tolist() for e in embeddings]

    @property
    def dimensions(self) -> int:
        return self.settings.embedding_dimensions


embedding_service = EmbeddingService()
