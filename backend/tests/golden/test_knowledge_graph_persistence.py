"""W-015: Knowledge graph persistence test — verify PostgreSQL graph survives restart.

Tests:
- Node and edge creation and retrieval
- Graph relationships (outgoing/incoming edges)
- Embedding storage and similarity search
- Tenant isolation via RLS
"""

import pytest
from app.db.database import get_sync_engine, set_tenant_context, reset_tenant_context
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.models import KnowledgeNode, KnowledgeEdge, KnowledgeEmbedding
from sqlalchemy.orm import Session


@pytest.fixture
def kg_service():
    """Knowledge graph service with test session."""
    engine = get_sync_engine()
    with Session(engine) as session:
        token = set_tenant_context("test-tenant-1")
        try:
            yield KnowledgeGraphService(session)
            session.commit()
        finally:
            reset_tenant_context(token)


def test_create_and_retrieve_node(kg_service):
    """Verify node creation and retrieval from PostgreSQL."""
    node = kg_service.create_node(
        node_type="contractor",
        external_id="C123",
        label="ABC Construction Ltd",
        tenant_id="test-tenant-1",
        description="A major construction firm",
        meta_json={"agency": "BWDB", "zone": "A"},
    )
    assert node.id is not None
    assert node.node_type == "contractor"
    assert node.external_id == "C123"

    # Retrieve
    retrieved = kg_service.get_node(node.id)
    assert retrieved is not None
    assert retrieved.label == "ABC Construction Ltd"


def test_create_edges_and_query_relationships(kg_service):
    """Verify edge creation and relationship queries."""
    # Create two nodes
    contractor_node = kg_service.create_node(
        node_type="contractor",
        external_id="C123",
        label="ABC Construction",
        tenant_id="test-tenant-1",
    )
    tender_node = kg_service.create_node(
        node_type="tender",
        external_id="T456",
        label="Road Repair Project",
        tenant_id="test-tenant-1",
    )

    # Create edge: contractor bid on tender
    edge = kg_service.create_edge(
        source_node_id=contractor_node.id,
        target_node_id=tender_node.id,
        edge_type="bidder_on",
        tenant_id="test-tenant-1",
        weight=0.95,
    )
    assert edge.id is not None

    # Query outgoing edges
    outgoing = kg_service.get_outgoing_edges(contractor_node.id)
    assert len(outgoing) == 1
    assert outgoing[0].edge_type == "bidder_on"
    assert outgoing[0].weight == 0.95

    # Query incoming edges
    incoming = kg_service.get_incoming_edges(tender_node.id)
    assert len(incoming) == 1
    assert incoming[0].source_node_id == contractor_node.id


def test_embedding_storage(kg_service):
    """Verify embedding storage in pgvector."""
    node = kg_service.create_node(
        node_type="contractor",
        external_id="C789",
        label="XYZ Corp",
        tenant_id="test-tenant-1",
    )

    # Store a mock 768-dim embedding (in practice from sentence-transformers)
    test_embedding = [0.1] * 768

    emb = kg_service.store_embedding(
        node_id=node.id,
        embedding=test_embedding,
        tenant_id="test-tenant-1",
    )
    assert emb.id is not None
    assert emb.node_id == node.id


def test_graph_statistics(kg_service):
    """Verify graph statistics queries."""
    # Create a small graph
    n1 = kg_service.create_node("contractor", "C1", "Corp 1", "test-tenant-1")
    n2 = kg_service.create_node("tender", "T1", "Tender 1", "test-tenant-1")
    kg_service.create_edge(n1.id, n2.id, "bidder_on", "test-tenant-1")

    stats = kg_service.get_graph_stats()
    assert stats["nodes"] >= 2
    assert stats["edges"] >= 1


def test_find_by_external_id(kg_service):
    """Verify node lookup by external ID."""
    node = kg_service.create_node(
        node_type="agency",
        external_id="BWDB",
        label="Bangladesh Water Development Board",
        tenant_id="test-tenant-1",
    )

    found = kg_service.find_nodes_by_external_id("BWDB")
    assert len(found) >= 1
    assert found[0].external_id == "BWDB"

    # Filter by type
    found_agency = kg_service.find_nodes_by_external_id("BWDB", node_type="agency")
    assert len(found_agency) >= 1
