"""Knowledge graph models for entity relationships and embeddings.

Replaces in-memory NetworkX graph with persistent PostgreSQL adjacency list + pgvector.
Tables:
- knowledge_nodes: entity nodes (tender, contractor, agency, zone, award)
- knowledge_edges: relationships between nodes (awarded_to, procured_by, located_in, similar_to)
- knowledge_embeddings: vector embeddings for semantic similarity search
"""

from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import JSON, Index, String, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class _UUIDStr(sa.TypeDecorator):
    """DB column is UUID; always returns Python str on read so FK and PK types match."""
    impl = sa.UUID()
    cache_ok = True

    def process_result_value(self, value, dialect):
        return str(value) if value is not None else None


class KnowledgeNode(Base, TimestampMixin, UUIDMixin):
    """Entity node in the knowledge graph.

    node_type: tender, contractor, agency, zone, award
    external_id: unique identifier in the source system (tender_id, contractor_id, etc.)
    metadata: arbitrary JSON for type-specific attributes
    """
    __tablename__ = "knowledge_nodes"
    __table_args__ = (
        Index("ix_knowledge_nodes_type_external_id", "node_type", "external_id"),
        Index("ix_knowledge_nodes_tenant_id", "tenant_id"),
    )

    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    outgoing_edges: Mapped[list["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge",
        foreign_keys="KnowledgeEdge.source_node_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge",
        foreign_keys="KnowledgeEdge.target_node_id",
        back_populates="target",
        cascade="all, delete-orphan",
    )
    embeddings: Mapped[list["KnowledgeEmbedding"]] = relationship(
        "KnowledgeEmbedding",
        back_populates="node",
        cascade="all, delete-orphan",
    )


class KnowledgeEdge(Base, TimestampMixin, UUIDMixin):
    """Directed edge (relationship) between two nodes.

    edge_type: awarded_to, procured_by, located_in, similar_to, bidder_on, etc.
    weight: relationship strength (0-1), for ranking similar nodes
    metadata: arbitrary JSON for edge-specific attributes (dates, amounts, etc.)
    """
    __tablename__ = "knowledge_edges"
    __table_args__ = (
        Index("ix_knowledge_edges_source_target", "source_node_id", "target_node_id"),
        Index("ix_knowledge_edges_type", "edge_type"),
        Index("ix_knowledge_edges_tenant_id", "tenant_id"),
    )

    source_node_id: Mapped[str] = mapped_column(_UUIDStr, ForeignKey("knowledge_nodes.id"), nullable=False)
    target_node_id: Mapped[str] = mapped_column(_UUIDStr, ForeignKey("knowledge_nodes.id"), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(50), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    source: Mapped[KnowledgeNode] = relationship(
        "KnowledgeNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges",
    )
    target: Mapped[KnowledgeNode] = relationship(
        "KnowledgeNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_edges",
    )


class KnowledgeEmbedding(Base, TimestampMixin, UUIDMixin):
    """Vector embedding for semantic similarity search.

    Uses pgvector to store dense embeddings (768-dim or configurable).
    embedding_model: identifies which model generated this (e.g., "sentence-transformers/all-MiniLM-L6-v2")
    """
    __tablename__ = "knowledge_embeddings"
    __table_args__ = (
        Index("ix_knowledge_embeddings_node_id", "node_id"),
        Index("ix_knowledge_embeddings_model", "embedding_model"),
        Index("ix_knowledge_embeddings_tenant_id", "tenant_id"),
    )

    node_id: Mapped[str] = mapped_column(_UUIDStr, ForeignKey("knowledge_nodes.id"), nullable=False)
    embedding: Mapped[str] = mapped_column(Text)  # JSON-serialized embedding vector. Upgrade to pgvector type in production.
    embedding_model: Mapped[str] = mapped_column(String(255), default="sentence-transformers/all-MiniLM-L6-v2")
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationship
    node: Mapped[KnowledgeNode] = relationship(
        "KnowledgeNode",
        back_populates="embeddings",
    )
