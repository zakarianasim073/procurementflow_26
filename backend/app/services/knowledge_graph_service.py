"""PostgreSQL-backed knowledge graph service.

Replaces in-memory NetworkX with persistent adjacency list + pgvector similarity.
W-015: Knowledge graph migration to PostgreSQL.
"""

import json
import logging
from typing import Optional, Dict, List, Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models import KnowledgeNode, KnowledgeEdge, KnowledgeEmbedding
from app.db.database import get_sync_engine, set_tenant_context

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """PostgreSQL knowledge graph — persistent, queryable, tenant-scoped."""

    def __init__(self, session: Session):
        self.session = session

    def create_node(
        self,
        node_type: str,
        external_id: str,
        label: str,
        tenant_id: str,
        description: Optional[str] = None,
        meta_json: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeNode:
        """Create a knowledge graph node."""
        node = KnowledgeNode(
            node_type=node_type,
            external_id=external_id,
            label=label,
            description=description,
            meta_json=meta_json or {},
            tenant_id=tenant_id,
        )
        self.session.add(node)
        self.session.flush()
        return node

    def create_edge(
        self,
        source_node_id,
        target_node_id,
        edge_type: str,
        tenant_id: str,
        weight: float = 1.0,
        meta_json: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEdge:
        """Create a directed edge between two nodes."""
        edge = KnowledgeEdge(
            source_node_id=str(source_node_id),
            target_node_id=str(target_node_id),
            edge_type=edge_type,
            weight=weight,
            meta_json=meta_json or {},
            tenant_id=tenant_id,
        )
        self.session.add(edge)
        self.session.flush()
        return edge

    def get_node(self, node_id) -> Optional[KnowledgeNode]:
        """Retrieve a node by ID."""
        stmt = select(KnowledgeNode).where(KnowledgeNode.id == str(node_id))
        return self.session.execute(stmt).scalar_one_or_none()

    def find_nodes_by_external_id(
        self,
        external_id: str,
        node_type: Optional[str] = None,
    ) -> List[KnowledgeNode]:
        """Find nodes by external ID (and optionally node type)."""
        stmt = select(KnowledgeNode).where(KnowledgeNode.external_id == external_id)
        if node_type:
            stmt = stmt.where(KnowledgeNode.node_type == node_type)
        return self.session.execute(stmt).scalars().all()

    def get_outgoing_edges(self, node_id) -> List[KnowledgeEdge]:
        """Get all outgoing edges from a node."""
        stmt = select(KnowledgeEdge).where(
            KnowledgeEdge.source_node_id == str(node_id)
        ).order_by(KnowledgeEdge.weight.desc())
        return self.session.execute(stmt).scalars().all()

    def get_incoming_edges(self, node_id) -> List[KnowledgeEdge]:
        """Get all incoming edges to a node."""
        stmt = select(KnowledgeEdge).where(
            KnowledgeEdge.target_node_id == str(node_id)
        ).order_by(KnowledgeEdge.weight.desc())
        return self.session.execute(stmt).scalars().all()

    def store_embedding(
        self,
        node_id,
        embedding: List[float],
        tenant_id: str,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> KnowledgeEmbedding:
        """Store a vector embedding for a node. Embeddings are JSON-serialized for TEXT storage."""
        emb = KnowledgeEmbedding(
            node_id=str(node_id),
            embedding=json.dumps(embedding),
            embedding_model=embedding_model,
            tenant_id=tenant_id,
        )
        self.session.add(emb)
        self.session.flush()
        return emb

    def get_similar_nodes(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[tuple[KnowledgeNode, float]]:
        """Find semantically similar nodes via cosine similarity (in-memory).

        Note: For production with pgvector installed, this can be optimized to use
        pgvector's <=> cosine distance operator in SQL.

        Returns list of (node, similarity_score) tuples, ordered by similarity desc.
        """
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            """Compute cosine similarity between two vectors."""
            if not a or not b:
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = sum(x ** 2 for x in a) ** 0.5
            mag_b = sum(x ** 2 for x in b) ** 0.5
            if mag_a == 0 or mag_b == 0:
                return 0.0
            return dot / (mag_a * mag_b)

        # Fetch all embeddings and compute similarity in-memory
        stmt = select(KnowledgeNode, KnowledgeEmbedding.embedding).join(
            KnowledgeEmbedding, KnowledgeNode.id == KnowledgeEmbedding.node_id
        )
        results = self.session.execute(stmt).all()

        similarities = []
        for node, embedding_json in results:
            try:
                embedding = json.loads(embedding_json) if isinstance(embedding_json, str) else embedding_json
                sim = cosine_similarity(query_embedding, embedding)
                if sim >= threshold:
                    similarities.append((node, sim))
            except (json.JSONDecodeError, TypeError):
                pass

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get basic graph statistics."""
        node_count = self.session.execute(select(func.count(KnowledgeNode.id))).scalar() or 0
        edge_count = self.session.execute(select(func.count(KnowledgeEdge.id))).scalar() or 0
        embedding_count = self.session.execute(select(func.count(KnowledgeEmbedding.id))).scalar() or 0

        return {
            "nodes": node_count,
            "edges": edge_count,
            "embeddings": embedding_count,
        }
