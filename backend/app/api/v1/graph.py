"""Phase 4-5: Knowledge Graph API — entity relationships and graph queries.

Endpoints:
  GET /graph/stats                          — relationship type counts
  GET /graph/neighbors?type=&id=&rel_type=   — entity neighbors
  GET /graph/path?from_type=&from_id=&to_type=&to_id=  — shortest path
  GET /graph/subgraph?type=&id=&depth=       — entity subgraph
  POST /graph/discover                       — trigger full discovery pass
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.crawler.database.connection import get_db_pool
from backend.crawler.database.normalizer import get_normalizer
from backend.crawler.services.relationship_engine import RelationshipEngine
from backend.crawler.framework.logger import get_logger

log = get_logger("graph.api")
router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


def _engine() -> RelationshipEngine:
    return RelationshipEngine()


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Get relationship counts by type across the entire graph."""
    engine = _engine()
    return await engine.get_stats()


@router.get("/neighbors")
async def get_neighbors(
    type: str = Query(..., description="Entity type (tender, company, award, etc.)"),
    id: int = Query(..., description="Entity ID"),
    rel_type: Optional[str] = Query(None, description="Filter by relationship type"),
) -> List[Dict[str, Any]]:
    """Get all neighboring entities connected to a given entity."""
    engine = _engine()
    rel_types = [rel_type] if rel_type else None
    return await engine.get_neighbors(type, id, rel_types)


@router.get("/path")
async def get_path(
    from_type: str = Query(..., description="Source entity type"),
    from_id: int = Query(..., description="Source entity ID"),
    to_type: str = Query(..., description="Target entity type"),
    to_id: int = Query(..., description="Target entity ID"),
    max_depth: int = Query(4, description="Maximum traversal depth"),
) -> Optional[List[Dict[str, Any]]]:
    """Find the shortest path between two entities."""
    engine = _engine()
    path = await engine.get_path(from_type, from_id, to_type, to_id, max_depth)
    if path is None:
        raise HTTPException(status_code=404, detail="No path found between entities")
    return path


@router.get("/subgraph")
async def get_subgraph(
    type: str = Query(..., description="Root entity type"),
    id: int = Query(..., description="Root entity ID"),
    depth: int = Query(2, description="Traversal depth"),
    rel_type: Optional[str] = Query(None, description="Filter by relationship type"),
) -> Dict[str, Any]:
    """Get the complete subgraph around an entity up to a given depth."""
    engine = _engine()
    rel_types = [rel_type] if rel_type else None
    return await engine.get_subgraph(type, id, depth, rel_types)


@router.post("/discover")
async def discover_relationships() -> Dict[str, Any]:
    """Run a full discovery pass across all pf_* entities."""
    engine = _engine()
    counts = await engine.discover_all()
    return {
        "status": "completed",
        "relationships_created": counts.get("_total", 0),
        "by_type": {k: v for k, v in counts.items() if k != "_total"},
    }


@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_details(
    entity_type: str,
    entity_id: int,
) -> Dict[str, Any]:
    """Get detailed information about an entity with its relationships.

    Returns the entity's core fields plus all relationship counts.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if entity_type == "tender":
            row = await conn.fetchrow(
                "SELECT id, tender_id, package_no, title, status, procuring_entity_id, "
                "category, procurement_nature, pe_office, district, agency_code "
                "FROM pf_tenders WHERE id=$1", entity_id)
        elif entity_type == "company":
            row = await conn.fetchrow(
                "SELECT id, name, registration_no, district FROM pf_companies WHERE id=$1", entity_id)
        elif entity_type == "procuring_entity":
            row = await conn.fetchrow(
                "SELECT id, name, office, agency_code FROM pf_procuring_entities WHERE id=$1", entity_id)
        elif entity_type == "award":
            row = await conn.fetchrow(
                "SELECT id, tender_id, package_no, company_id, procuring_entity_id, "
                "title, contract_value, award_date FROM pf_awards WHERE id=$1", entity_id)
        else:
            row = await conn.fetchrow(
                f"SELECT * FROM {entity_type} WHERE id=$1", entity_id)

    if not row:
        raise HTTPException(status_code=404, detail=f"{entity_type} #{entity_id} not found")

    entity = dict(row)

    engine = _engine()
    neighbors = await engine.get_neighbors(entity_type, entity_id)
    entity["relationships"] = {
        "total": len(neighbors),
        "by_type": {}
    }
    for n in neighbors:
        rt = n["relationship_type"]
        if rt not in entity["relationships"]["by_type"]:
            entity["relationships"]["by_type"][rt] = {"outgoing": 0, "incoming": 0}
        entity["relationships"]["by_type"][rt][n["direction"]] += 1

    return entity
