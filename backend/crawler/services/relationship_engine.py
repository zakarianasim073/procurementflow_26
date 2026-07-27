"""Phase 4 — Relationship Engine.

Discovers, stores, and queries typed relationships between normalized
pf_* entities. Supports FK-based links (award.company_id → company.id),
string-based links (award.tender_id = tender.tender_id), and fuzzy
name matching for implicit connections.

All discovered edges are stored in pf_relationships for fast graph
traversal without N+1 FK joins.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ..database.connection import get_db_pool
from ..database.normalizer import Normalizer
from ..framework.logger import get_logger

log = get_logger("crawler.services.relationship")

# ── Relationship type constants ──

# Tender → Entity
REL_TENDER_PE = "procured_by"          # tender → procuring_entity
REL_TENDER_LOT = "has_lot"             # tender → lot
REL_TENDER_APP = "part_of_app"         # tender → app
REL_TENDER_PKG = "has_package"         # tender → package

# Award → Entity
REL_AWARD_COMPANY = "awarded_to"       # award → company
REL_AWARD_TENDER = "belongs_to_tender" # award → tender (by tender_id string)
REL_AWARD_PE = "awarded_by"           # award → procuring_entity

# Experience → Entity
REL_EXP_COMPANY = "has_experience"     # experience → company
REL_EXP_PE = "experienced_at"         # experience → procuring_entity

# Debarment → Entity
REL_DEB_COMPANY = "has_debarment"      # debarment → company

# Document → Entity
REL_DOC_TENDER = "has_document"        # document → tender

# Company → Tender (implicit, from awards)
REL_COMPANY_TENDER = "bid_on"          # company → tender (via award)

# Inverse relationship types (for graph traversal)
INVERSE_MAP = {
    REL_TENDER_PE: "manages_tender",
    REL_TENDER_LOT: "belongs_to_tender",
    REL_TENDER_APP: "contains_tender",
    REL_AWARD_COMPANY: "won_award",
    REL_AWARD_TENDER: "has_award",
    REL_AWARD_PE: "issued_award",
    REL_EXP_COMPANY: "has_experience_record",
    REL_EXP_PE: "verified_experience",
    REL_DEB_COMPANY: "has_debarment_record",
    REL_DOC_TENDER: "is_document_of",
    REL_COMPANY_TENDER: "was_bid_by",
}


class RelationshipEngine:
    """Discovers and manages relationships between pf_* entities."""

    def __init__(self, pool=None):
        self._pool = pool
        self._norm = Normalizer()

    async def _get_pool(self):
        if self._pool is None:
            self._pool = await get_db_pool()
        return self._pool

    # ── Discovery Methods ──────────────────────────────────────────

    async def discover_all(self, batch_size: int = 500) -> Dict[str, int]:
        """Run all discovery passes and return counts per relationship type."""
        counts: Dict[str, int] = {}

        for method_name in [
            "discover_tender_pe",
            "discover_tender_lot",
            "discover_award_company",
            "discover_award_tender",
            "discover_award_tender_by_package",
            "discover_award_pe",
            "discover_experience_company",
            "discover_experience_pe",
            "discover_debarment_company",
            "discover_document_tender",
            "discover_award_experience_by_company",
        ]:
            method = getattr(self, method_name)
            cnt = await method(batch_size)
            if cnt > 0:
                counts[method_name.replace("discover_", "")] = cnt
                log.info("discovered_relationships", method=method_name, count=cnt)

        total = sum(counts.values())
        log.info("discovery_complete", total=total, types=list(counts.keys()))
        counts["_total"] = total

        # Keep the adjacency materialized view in sync so path/subgraph queries
        # see freshly discovered edges.
        await self.refresh_graph()
        return counts

    async def refresh_graph(self) -> bool:
        """Refresh the pf_entity_graph materialized view.

        Tries CONCURRENTLY first (non-blocking, needs unique index); falls back
        to a plain refresh if the view has never been populated.
        """
        pool = await self._get_pool()
        try:
            await pool.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY pf_entity_graph")
            log.info("entity_graph_refreshed", mode="concurrent")
            return True
        except Exception as e:
            log.warning("entity_graph_concurrent_refresh_failed", error=str(e))
            try:
                await pool.execute("REFRESH MATERIALIZED VIEW pf_entity_graph")
                log.info("entity_graph_refreshed", mode="plain")
                return True
            except Exception as e2:
                log.error("entity_graph_refresh_failed", error=str(e2))
                return False

    async def discover_tender_pe(self, batch_size: int = 500) -> int:
        """Link tenders to their procuring entities."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT t.id AS source_id, t.procuring_entity_id AS target_id
            FROM pf_tenders t
            WHERE t.procuring_entity_id IS NOT NULL
        """)
        return await self._bulk_upsert(
            rows, "tender", "procuring_entity", REL_TENDER_PE, "fk_scan", batch_size,
        )

    async def discover_tender_lot(self, batch_size: int = 500) -> int:
        """Link tenders to their lots."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT l.tender_id AS source_id, l.id AS target_id
            FROM pf_lots l
        """)
        return await self._bulk_upsert(
            rows, "tender", "lot", REL_TENDER_LOT, "fk_scan", batch_size,
        )

    async def discover_award_company(self, batch_size: int = 500) -> int:
        """Link awards to their winning companies."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT a.id AS source_id, a.company_id AS target_id
            FROM pf_awards a
            WHERE a.company_id IS NOT NULL
        """)
        return await self._bulk_upsert(
            rows, "award", "company", REL_AWARD_COMPANY, "fk_scan", batch_size,
        )

    async def discover_award_tender(self, batch_size: int = 500) -> int:
        """Link awards to their parent tenders via tender_id string match."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT a.id AS source_id, t.id AS target_id
            FROM pf_awards a
            JOIN pf_tenders t ON t.tender_id = a.tender_id
        """)
        return await self._bulk_upsert(
            rows, "award", "tender", REL_AWARD_TENDER, "string_match", batch_size,
        )

    async def discover_award_pe(self, batch_size: int = 500) -> int:
        """Link awards to procuring entities."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT a.id AS source_id, a.procuring_entity_id AS target_id
            FROM pf_awards a
            WHERE a.procuring_entity_id IS NOT NULL
        """)
        return await self._bulk_upsert(
            rows, "award", "procuring_entity", REL_AWARD_PE, "fk_scan", batch_size,
        )

    async def discover_experience_company(self, batch_size: int = 500) -> int:
        """Link experience records to their companies."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT e.id AS source_id, e.company_id AS target_id
            FROM pf_experience e
            WHERE e.company_id IS NOT NULL
        """)
        return await self._bulk_upsert(
            rows, "experience", "company", REL_EXP_COMPANY, "fk_scan", batch_size,
        )

    async def discover_experience_pe(self, batch_size: int = 500) -> int:
        """Link experience records to procuring entities."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT e.id AS source_id, e.procuring_entity_id AS target_id
            FROM pf_experience e
            WHERE e.procuring_entity_id IS NOT NULL
        """)
        return await self._bulk_upsert(
            rows, "experience", "procuring_entity", REL_EXP_PE, "fk_scan", batch_size,
        )

    async def discover_debarment_company(self, batch_size: int = 500) -> int:
        """Link debarments to their companies."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT d.id AS source_id, d.company_id AS target_id
            FROM pf_debarments d
            WHERE d.company_id IS NOT NULL
        """)
        return await self._bulk_upsert(
            rows, "debarment", "company", REL_DEB_COMPANY, "fk_scan", batch_size,
        )

    async def discover_document_tender(self, batch_size: int = 500) -> int:
        """Link documents to their tenders via tender_id string match."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT d.id AS source_id, t.id AS target_id
            FROM pf_documents d
            JOIN pf_tenders t ON t.tender_id = d.tender_id
        """)
        return await self._bulk_upsert(
            rows, "document", "tender", REL_DOC_TENDER, "string_match", batch_size,
        )

    async def discover_award_tender_by_package(self, batch_size: int = 500) -> int:
        """Link awards to tenders via package_no (universal join key, ADR-016)."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT a.id AS source_id, t.id AS target_id
            FROM pf_awards a
            JOIN pf_tenders t ON t.package_no = a.package_no
            WHERE a.package_no IS NOT NULL
              AND (a.tender_id IS NULL OR a.tender_id = '' OR a.tender_id != t.tender_id)
        """)
        return await self._bulk_upsert(
            rows, "award", "tender", REL_AWARD_TENDER, "package_match", batch_size,
        )

    async def discover_award_experience_by_company(self, batch_size: int = 500) -> int:
        """Link awards to experience records via company_id (both reference same company)."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT a.id AS source_id, e.id AS target_id
            FROM pf_awards a
            JOIN pf_experience e ON e.company_id = a.company_id
            WHERE a.company_id IS NOT NULL
        """)
        return await self._bulk_upsert(
            rows, "award", "experience", "has_experience_match", "company_match", batch_size,
        )

    async def discover_company_tenders(self, batch_size: int = 500) -> int:
        """Link companies to tenders they've bid on/awarded (via awards)."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT DISTINCT a.company_id AS source_id, t.id AS target_id
            FROM pf_awards a
            JOIN pf_tenders t ON t.tender_id = a.tender_id
            WHERE a.company_id IS NOT NULL
        """)
        return await self._bulk_upsert(
            rows, "company", "tender", REL_COMPANY_TENDER, "fk_scan", batch_size,
        )

    # ── Bulk Upsert ────────────────────────────────────────────────

    async def _bulk_upsert(
        self,
        rows: List[Dict[str, Any]],
        source_type: str,
        target_type: str,
        rel_type: str,
        discovered_by: str,
        batch_size: int = 500,
    ) -> int:
        """Upsert discovered relationships in batches."""
        if not rows:
            return 0

        pool = await self._get_pool()
        now = datetime.utcnow()
        count = 0

        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            values_list = []
            for row in batch:
                sid = row.get("source_id") or row.get("id")
                tid = row.get("target_id")
                if sid is None or tid is None:
                    continue
                data_hash = uuid4().hex[:16]
                values_list.append(
                    f"('{source_type}', {sid}, '{target_type}', {tid}, "
                    f"'{rel_type}', '{discovered_by}', "
                    f"'{now.isoformat()}', '{data_hash}')"
                )

            if not values_list:
                continue

            sql = f"""
                INSERT INTO pf_relationships
                    (source_type, source_id, target_type, target_id,
                     relationship_type, discovered_by, created_at, data_hash)
                VALUES {', '.join(values_list)}
                ON CONFLICT (source_type, source_id, target_type, target_id, relationship_type)
                DO NOTHING
            """
            await pool.execute(sql)
            count += len(values_list)

        return count

    # ── Query Methods ──────────────────────────────────────────────

    async def get_neighbors(
        self,
        entity_type: str,
        entity_id: int,
        rel_types: Optional[List[str]] = None,
        max_depth: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get neighboring entities for a given entity, optionally filtered by relationship type."""
        pool = await self._get_pool()
        rel_filter = ""
        params: List[Any] = [entity_type, entity_id]
        if rel_types:
            placeholders = [f"${i+3}" for i in range(len(rel_types))]
            rel_filter = f" AND r.relationship_type IN ({','.join(placeholders)})"
            params.extend(rel_types)

        rows = await pool.fetch(
            f"""
            SELECT r.id, r.source_type, r.source_id, r.target_type, r.target_id,
                   r.relationship_type, r.confidence, r.metadata, r.discovered_by
            FROM pf_relationships r
            WHERE (
                (r.source_type = $1 AND r.source_id = $2)
                OR (r.target_type = $1 AND r.target_id = $2)
            )
            AND NOT r.is_deleted
            {rel_filter}
            ORDER BY r.confidence DESC
            """,
            *params,
        )

        result = []
        for r in rows:
            is_source = (r["source_type"] == entity_type and r["source_id"] == entity_id)
            result.append({
                "relationship_id": r["id"],
                "relationship_type": r["relationship_type"],
                "direction": "outgoing" if is_source else "incoming",
                "neighbor_type": r["target_type"] if is_source else r["source_type"],
                "neighbor_id": r["target_id"] if is_source else r["source_id"],
                "confidence": float(r["confidence"]) if r["confidence"] else 1.0,
                "metadata": r["metadata"],
                "discovered_by": r["discovered_by"],
            })
        return result

    async def get_path(
        self,
        from_type: str,
        from_id: int,
        to_type: str,
        to_id: int,
        max_depth: int = 4,
    ) -> Optional[List[Dict[str, Any]]]:
        """BFS shortest path between two entities using the materialized graph view."""
        pool = await self._get_pool()

        rows = await pool.fetch(
            """
            WITH RECURSIVE path_search AS (
                SELECT
                    entity_type, entity_id, related_type, related_id,
                    relationship_type, confidence,
                    ARRAY[ROW(entity_type, entity_id, relationship_type, related_type, related_id)::text] AS trail,
                    1 AS depth
                FROM pf_entity_graph
                WHERE entity_type = $1 AND entity_id = $2

                UNION ALL

                SELECT
                    g.entity_type, g.entity_id, g.related_type, g.related_id,
                    g.relationship_type, g.confidence,
                    p.trail || ROW(g.entity_type, g.entity_id, g.relationship_type, g.related_type, g.related_id)::text,
                    p.depth + 1
                FROM pf_entity_graph g
                JOIN path_search p
                    ON p.related_type = g.entity_type AND p.related_id = g.entity_id
                WHERE p.depth < $5
                  AND NOT (g.entity_type = $1 AND g.entity_id = $2)
            )
            SELECT trail, depth
            FROM path_search
            WHERE related_type = $3 AND related_id = $4
            ORDER BY depth
            LIMIT 1
            """,
            from_type, from_id, to_type, to_id, max_depth,
        )

        if not rows:
            return None

        trail = rows[0]["trail"]
        return [
            {
                "step": i,
                "from_type": seg[0].split(",")[0].strip("()\""),
                "from_id": int(seg[1]),
                "relationship": seg[2],
                "to_type": seg[3],
                "to_id": int(seg[4].rstrip(")")),
            }
            for i, seg in enumerate(trail)
        ]

    async def get_subgraph(
        self,
        entity_type: str,
        entity_id: int,
        max_depth: int = 2,
        rel_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get the full subgraph around an entity up to max_depth."""
        pool = await self._get_pool()
        rel_filter = ""
        params: List[Any] = [entity_type, entity_id, max_depth]
        if rel_types:
            placeholders = [f"${i+4}" for i in range(len(rel_types))]
            rel_filter = f" AND g.relationship_type IN ({','.join(placeholders)})"
            params.extend(rel_types)

        rows = await pool.fetch(
            f"""
            WITH RECURSIVE subgraph AS (
                SELECT
                    entity_type, entity_id, related_type, related_id,
                    relationship_type, confidence, 1 AS depth
                FROM pf_entity_graph g
                WHERE g.entity_type = $1 AND g.entity_id = $2
                  AND NOT (g.related_type = $1 AND g.related_id = $2)
                {rel_filter}

                UNION ALL

                SELECT
                    g.entity_type, g.entity_id, g.related_type, g.related_id,
                    g.relationship_type, g.confidence, s.depth + 1
                FROM pf_entity_graph g
                JOIN subgraph s
                    ON s.related_type = g.entity_type AND s.related_id = g.entity_id
                WHERE s.depth < $3
                  AND NOT (g.entity_type = $1 AND g.entity_id = $2)
                {rel_filter}
            )
            SELECT DISTINCT ON (entity_type, entity_id, related_type, related_id, relationship_type)
                entity_type, entity_id, related_type, related_id,
                relationship_type, confidence, depth
            FROM subgraph
            ORDER BY entity_type, entity_id, related_type, related_id, relationship_type, depth
            """,
            *params,
        )

        nodes: Dict[str, set] = {}
        edges: List[Dict[str, Any]] = []
        for r in rows:
            nodes.setdefault(r["entity_type"], set()).add(r["entity_id"])
            nodes.setdefault(r["related_type"], set()).add(r["related_id"])
            edges.append({
                "source_type": r["entity_type"],
                "source_id": r["entity_id"],
                "target_type": r["related_type"],
                "target_id": r["related_id"],
                "relationship_type": r["relationship_type"],
                "confidence": float(r["confidence"]) if r["confidence"] else 1.0,
                "depth": r["depth"],
            })

        return {
            "root": {"type": entity_type, "id": entity_id},
            "nodes": {t: sorted(ids) for t, ids in nodes.items()},
            "edges": edges,
            "node_count": sum(len(ids) for ids in nodes.values()),
            "edge_count": len(edges),
        }

    # ── Stats ──────────────────────────────────────────────────────

    async def get_stats(self) -> Dict[str, Any]:
        """Get relationship counts by type."""
        pool = await self._get_pool()
        rows = await pool.fetch("""
            SELECT relationship_type, COUNT(*) AS cnt
            FROM pf_relationships
            WHERE NOT is_deleted
            GROUP BY relationship_type
            ORDER BY cnt DESC
        """)
        total = sum(r["cnt"] for r in rows)
        return {
            "total_relationships": total,
            "types": {r["relationship_type"]: r["cnt"] for r in rows},
        }
