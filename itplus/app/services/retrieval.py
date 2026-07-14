"""Vector retrieval from pgvector."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from itplus.app.services.embedding import embedding_service


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
        category: str | None = None,
    ) -> list[dict]:
        query_embedding = embedding_service.embed_text(query)
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        category_filter = ""
        params: dict = {"embedding": embedding_str, "top_k": top_k}
        if category and category.strip().lower() != "general":
            category_filter = "AND d.category = :category"
            params["category"] = category.strip().lower()

        sql = text(f"""
            SELECT
                dc.id AS chunk_id,
                dc.content,
                dc.metadata,
                d.id AS document_id,
                d.filename AS document_name,
                d.category AS document_category,
                1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.status = 'ready'
              AND dc.embedding IS NOT NULL
              {category_filter}
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)

        result = self.db.execute(
            sql,
            params,
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
                "category": getattr(row, "document_category", None),
                "page": metadata.get("page") or metadata.get("sheet"),
                "score": round(score, 4),
            })
        return hits

    def search_multi(
        self,
        query: str,
        categories: list[str] | None = None,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[dict]:
        """Search one category or merge results across several (deduped by chunk)."""
        if not categories or any(c.strip().lower() == "general" for c in categories):
            return self.search(query, top_k=top_k, min_score=min_score)

        merged: dict[str, dict] = {}
        per_cat = max(3, top_k // len(categories) + 1)
        for cat in categories:
            for hit in self.search(query, top_k=per_cat, min_score=min_score, category=cat):
                chunk_id = str(hit["chunk_id"])
                existing = merged.get(chunk_id)
                if not existing or hit["score"] > existing["score"]:
                    merged[chunk_id] = hit

        return sorted(merged.values(), key=lambda h: h["score"], reverse=True)[:top_k]

    def fetch_tabular_file_chunks(self) -> list[dict]:
        """Load chunks from known tabular report files (CSV/Excel)."""
        sql = text("""
            SELECT
                dc.id AS chunk_id,
                dc.content,
                d.id AS document_id,
                d.filename AS document_name,
                d.category AS document_category,
                0.95 AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.status = 'ready'
              AND (
                d.filename ILIKE '%ventas%'
                OR d.filename ILIKE '%financiero%'
                OR d.filename ILIKE '%metas%'
                OR d.filename ILIKE '%quiebre%'
                OR d.filename ILIKE '%ecommerce%'
                OR d.filename ILIKE '%sales%'
              )
        """)
        result = self.db.execute(sql)
        hits: list[dict] = []
        for row in result:
            metadata = row.metadata if hasattr(row, "metadata") else {}
            hits.append({
                "chunk_id": row.chunk_id,
                "content": row.content,
                "document_id": row.document_id,
                "document_name": row.document_name,
                "category": getattr(row, "document_category", None),
                "page": metadata.get("page") if isinstance(metadata, dict) else None,
                "score": float(row.score),
            })
        return hits

    def search_for_analytics(
        self,
        question: str,
        category: str | None = None,
    ) -> list[dict]:
        """Broader retrieval for analytical questions (Phase 2)."""
        hits = self.search(question, top_k=16, min_score=0.24, category=category)
        seen = {h["chunk_id"] for h in hits}

        for h in self.fetch_tabular_file_chunks():
            if h["chunk_id"] not in seen:
                hits.append(h)
                seen.add(h["chunk_id"])

        q = question.lower()
        extra_queries: list[str] = []
        if any(w in q for w in ("compar", "ventas", "2025", "2026", "ene", "mar", "trimestre", "junio", "ecommerce")):
            extra_queries.extend([
                "ventas enero marzo monto_clp",
                "ventas 2025 2026",
                "ecommerce sales category price quantity",
                "total_q1 var_vs_2025 ingresos ventas",
            ])
        if any(w in q for w in ("meta", "vendedor", "cumpli", "q1")):
            extra_queries.append("vendedores metas cumplimiento q1")
        if any(w in q for w in ("quiebre", "tipo", "sap", "wms")):
            extra_queries.append("quiebres tipo SAP WMS familia")

        for eq in extra_queries:
            for h in self.search(eq, top_k=14, min_score=0.20, category=category):
                if h["chunk_id"] not in seen:
                    hits.append(h)
                    seen.add(h["chunk_id"])

        return hits
