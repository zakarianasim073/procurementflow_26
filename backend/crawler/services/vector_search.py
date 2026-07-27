from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Dict, List, Optional

from ..database.connection import get_db_pool
from ..framework.logger import get_logger

log = get_logger("crawler.services.vector_search")

EMBEDDING_DIM = 384


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]{2,}", text.lower())


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class VectorSearch:
    """Embedding-based semantic search.

    pgvector is not installed on the target PostgreSQL instance, so
    embeddings are stored as native FLOAT[] arrays and similarity is
    computed in Python. This is correct for the moderate corpus sizes
    we handle per query; if pgvector becomes available, swap the
    storage column to vector(384) and use the <=> operator instead.
    """

    def __init__(self, pool=None):
        self._pool = pool

    async def _get_pool(self):
        if self._pool is None:
            self._pool = await get_db_pool()
        return self._pool

    def embed_text(self, text: str) -> List[float]:
        tokens = _tokenize(text)
        if not tokens:
            return [0.0] * EMBEDDING_DIM

        vec = [0.0] * EMBEDDING_DIM
        bucket_counts = [0] * EMBEDDING_DIM

        for token in tokens:
            h = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(0, len(h) - 1, 2):
                idx = (h[i] | (h[i + 1] << 8)) % EMBEDDING_DIM
                sign = 1 if (h[(i + 1) % len(h)] & 1) == 0 else -1
                vec[idx] += float(sign)
                bucket_counts[idx] += 1

        norm_sq = 0.0
        for i in range(EMBEDDING_DIM):
            if bucket_counts[i] > 0:
                vec[i] = math.log(1.0 + abs(vec[i])) * (1.0 if vec[i] >= 0 else -1.0)
            norm_sq += vec[i] * vec[i]

        if norm_sq > 0:
            inv_norm = 1.0 / math.sqrt(norm_sq)
            for i in range(EMBEDDING_DIM):
                vec[i] *= inv_norm

        return vec

    async def store_embedding(
        self,
        entity_type: str,
        entity_id: int,
        text: str,
        doc_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        pool = await self._get_pool()
        embedding = self.embed_text(text)
        row_id = await pool.fetchval(
            """
            INSERT INTO pf_document_embeddings
                (entity_type, entity_id, doc_type, text_content, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5::float[], $6::jsonb)
            ON CONFLICT (entity_type, entity_id, doc_type)
            DO UPDATE SET embedding = EXCLUDED.embedding, text_content = EXCLUDED.text_content,
                          metadata = EXCLUDED.metadata, updated_at = NOW()
            RETURNING id
            """,
            entity_type,
            entity_id,
            doc_type,
            text,
            embedding,
            json.dumps(metadata or {}),
        )
        log.info("embedding_stored", entity_type=entity_type, entity_id=entity_id, doc_type=doc_type)
        return row_id

    async def search_similar(
        self,
        query_text: str,
        entity_type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        pool = await self._get_pool()
        query_embedding = self.embed_text(query_text)

        type_filter = ""
        params: List[Any] = []
        if entity_type:
            type_filter = "WHERE entity_type = $1"
            params.append(entity_type)

        rows = await pool.fetch(
            f"""
            SELECT id, entity_type, entity_id, doc_type, embedding, metadata, created_at
            FROM pf_document_embeddings
            {type_filter}
            """,
            *params,
        )

        results = []
        for r in rows:
            emb = list(r["embedding"]) if r["embedding"] else None
            if not emb:
                continue
            sim = cosine_similarity(query_embedding, emb)
            results.append({
                "id": r["id"],
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "doc_type": r["doc_type"],
                "similarity": round(sim, 6),
                "metadata": r["metadata"],
                "created_at": r["created_at"],
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    async def find_similar_tenders(self, tender_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
        pool = await self._get_pool()
        rows = await pool.fetch(
            "SELECT text_content FROM pf_document_embeddings WHERE entity_type = 'tender' AND entity_id = $1 LIMIT 1",
            tender_id,
        )
        if not rows:
            return []
        query_text = rows[0]["text_content"] or ""
        results = await self.search_similar(query_text, entity_type="tender", top_k=top_k + 1)
        return [r for r in results if r["entity_id"] != tender_id][:top_k]

    async def find_similar_companies(self, company_id: int, top_k: int = 10) -> List[Dict[str, Any]]:
        pool = await self._get_pool()
        rows = await pool.fetch(
            "SELECT text_content FROM pf_document_embeddings WHERE entity_type = 'company' AND entity_id = $1 LIMIT 1",
            company_id,
        )
        if not rows:
            return []
        query_text = rows[0]["text_content"] or ""
        results = await self.search_similar(query_text, entity_type="company", top_k=top_k + 1)
        return [r for r in results if r["entity_id"] != company_id][:top_k]

    async def find_similar_documents(
        self,
        doc_text: str,
        doc_type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        return await self.search_similar(doc_text, entity_type="document", top_k=top_k)
