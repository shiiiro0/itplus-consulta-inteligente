"""Vector retrieval from pgvector."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from itplus.app.services.embedding import embedding_service


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(self, query: str, top_k: int = 5, min_score: float = 0.3) -> list[dict]:
        query_embedding = embedding_service.embed_text(query)
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = text("""
            SELECT
                dc.id AS chunk_id,
                dc.content,
                dc.metadata,
                d.id AS document_id,
                d.filename AS document_name,
                1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.status = 'ready'
              AND dc.embedding IS NOT NULL
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        result = self.db.execute(
            sql,
            {"embedding": embedding_str, "top_k": top_k},
        )

        hits: list[dict] = []
        for row in result:
            score = float(row.score) if row.score else 0.0
            if score < min_score:
                continue
            metadata = row.metadata or {}
            hits.append({
                "chunk_id": row.chunk_id,
                "content": row.content,
                "document_id": row.document_id,
                "document_name": row.document_name,
                "page": metadata.get("page"),
                "score": round(score, 4),
            })
        return hits
