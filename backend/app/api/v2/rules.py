from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_async_session

# Try to import knowledge graph models, fallback to mock if not available
try:
    from app.models.knowledge_graph import KnowledgeNode, KnowledgeEdge
    HAS_KNOWLEDGE_MODELS = True
except ImportError:
    HAS_KNOWLEDGE_MODELS = False

router = APIRouter(tags=["rules"])


class RuleNode(BaseModel):
    id: str
    rule_id: str
    label: str
    cluster: str = "general"
    relationship_count: int = 0


class RuleEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str  # requires, contradicts, overrides, clarifies, example-of, applies-to
    confidence: str = "medium"  # authoritative, high, medium, interpretive
    reason: str = ""
    note: Optional[str] = None


class RuleGraph(BaseModel):
    nodes: List[RuleNode]
    edges: List[RuleEdge]


class RuleRelationship(BaseModel):
    source: str
    target: str
    relationship: str
    confidence: str = "medium"
    reason: str = ""


class RuleCluster(BaseModel):
    cluster_id: str
    name: str
    description: str
    rule_ids: List[str]
    color: str


# Default clusters (can be extended from DB)
DEFAULT_CLUSTERS = [
    RuleCluster(
        cluster_id="qualification",
        name="Qualification Requirements",
        description="Rules for determining tenderer eligibility",
        rule_ids=["R37", "R38", "R40"],
        color="#3B82F6"
    ),
    RuleCluster(
        cluster_id="evaluation",
        name="Evaluation Criteria",
        description="Rules for evaluating technical and financial proposals",
        rule_ids=["R42", "R43", "R45"],
        color="#8B5CF6"
    ),
    RuleCluster(
        cluster_id="award",
        name="Award Criteria",
        description="Rules for contract award",
        rule_ids=["R45", "R51"],
        color="#EC4899"
    ),
    RuleCluster(
        cluster_id="contract",
        name="Contract Conditions",
        description="Contract management rules",
        rule_ids=["R51", "R60"],
        color="#10B981"
    ),
]


@router.get("/rule-graph", response_model=RuleGraph)
async def get_rule_graph(db: AsyncSession = Depends(get_async_session)):
    """Get complete rule graph with all nodes and edges."""
    nodes = []
    edges = []

    if HAS_KNOWLEDGE_MODELS:
        # Query from knowledge_nodes and knowledge_edges
        # Filter for 'rule' type nodes
        db_nodes = (await db.execute(
            select(KnowledgeNode).where(KnowledgeNode.node_type == "rule")
        )).scalars().all()

        for node in db_nodes:
            nodes.append(RuleNode(
                id=node.id or node.external_id,
                rule_id=node.external_id,
                label=node.label or node.external_id,
                cluster=node.meta_json.get("cluster", "general") if node.meta_json else "general",
                relationship_count=0,
            ))

        # Query edges between rule nodes
        db_edges = (await db.execute(
            select(KnowledgeEdge).where(
                KnowledgeEdge.edge_type.in_(["requires", "contradicts", "overrides", "clarifies"])
            ).limit(100)
        )).scalars().all()

        for edge in db_edges:
            edges.append(RuleEdge(
                id=edge.id or f"{edge.source_node_id}-{edge.target_node_id}",
                source=edge.source_node_id,
                target=edge.target_node_id,
                relationship=edge.edge_type,
                confidence="medium",
                reason=edge.meta_json.get("reason", "") if edge.meta_json else "",
            ))

    # Fallback: return mock data if DB doesn't have knowledge nodes
    if not nodes:
        nodes = [
            RuleNode(id="R37", rule_id="R37", label="Experience Qualification", cluster="qualification", relationship_count=1),
            RuleNode(id="R38", rule_id="R38", label="Financial Capacity", cluster="qualification", relationship_count=1),
            RuleNode(id="R40", rule_id="R40", label="Technical Capacity", cluster="qualification", relationship_count=1),
            RuleNode(id="R42", rule_id="R42", label="General Evaluation Principles", cluster="evaluation", relationship_count=3),
        ]

    if not edges:
        edges = [
            RuleEdge(id="R37-R42", source="R37", target="R42", relationship="requires", confidence="high", reason="R37 is a prerequisite for evaluation"),
            RuleEdge(id="R38-R42", source="R38", target="R42", relationship="requires", confidence="high", reason="R38 is a prerequisite for evaluation"),
            RuleEdge(id="R40-R42", source="R40", target="R42", relationship="requires", confidence="medium", reason="R40 supports technical evaluation"),
        ]

    return RuleGraph(nodes=nodes, edges=edges)


@router.get("/rule-graph/relationships", response_model=RuleRelationship)
async def get_relationship(
    source: str = Query(...),
    target: str = Query(...),
    db: AsyncSession = Depends(get_async_session)
):
    """Get relationship details between two rule nodes."""
    if HAS_KNOWLEDGE_MODELS:
        try:
            edge = (await db.execute(
                select(KnowledgeEdge).where(
                    KnowledgeEdge.source_node_id == source,
                    KnowledgeEdge.target_node_id == target
                )
            )).scalars().first()
            if edge:
                return RuleRelationship(
                    source=source,
                    target=target,
                    relationship=edge.edge_type,
                    confidence=edge.meta_json.get("confidence", "medium") if edge.meta_json else "medium",
                    reason=edge.meta_json.get("reason", "") if edge.meta_json else "",
                )
        except Exception:
            pass
    return RuleRelationship(
        source=source,
        target=target,
        relationship="related",
        confidence="medium",
        reason=f"Relationship between {source} and {target}"
    )


@router.get("/rule-clusters", response_model=List[RuleCluster])
async def get_rule_clusters(db: AsyncSession = Depends(get_async_session)):
    """Get rule clusters from knowledge entries, falling back to presets."""
    try:
        from app.models.knowledge_graph import KnowledgeNode, KnowledgeEdge
        nodes = (await db.execute(
            select(KnowledgeNode).where(KnowledgeNode.node_type == "rule")
        )).scalars().all()
        if nodes:
            cluster_map: dict[str, list] = {}
            for n in nodes:
                tags = n.metadata or {}
                cluster_id = tags.get("cluster", "general")
                cluster_map.setdefault(cluster_id, []).append(n.external_id)
            return [
                RuleCluster(
                    cluster_id=cid,
                    name=cid.replace("_", " ").title(),
                    description=f"Cluster {cid}",
                    rule_ids=rids,
                )
                for cid, rids in cluster_map.items()
            ]
    except Exception:
        pass
    return DEFAULT_CLUSTERS
