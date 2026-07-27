"""Knowledge graph ETL — backfill from existing contractor/tender/award data.

W-015: Populates knowledge_nodes and knowledge_edges from procurement schema.
Relationships:
- Contractor → Tenders (bidder_on)
- Contractor → Awards (awarded_to)
- Agency → Tenders (procured_by)
- Tender → Awards (award_issued_for)
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import Session

from app.models import (
    KnowledgeNode, KnowledgeEdge,
    Contractor, ProcurementTender, AwardRecordV2, Agency,
)
from app.db.database import get_sync_engine, set_tenant_context, reset_tenant_context

logger = logging.getLogger(__name__)


class KnowledgeGraphETL:
    """ETL pipeline to backfill knowledge graph from procurement data."""

    def __init__(self, session: Session):
        self.session = session
        self.node_cache: Dict[tuple, UUID] = {}  # (type, external_id) → node_id

    @staticmethod
    def _ext(value: str) -> str:
        """Normalize an external_id to fit the String(255) column; used for both
        node creation and edge lookups so cache keys always match."""
        return (value or "")[:255]


    def backfill_all_sql(self, tenant_id: str) -> Dict[str, int]:
        """Full-table set-based backfill (ALL rows — 998K awards, 727K tenders).

        Uses INSERT..SELECT so PostgreSQL does the joins; no per-row ORM objects.
        Idempotent: clears this tenant's graph first. Nodes are deduped by
        external_id (DISTINCT ON) so edge joins can't fan out.
        """
        s = self.session
        stats: Dict[str, int] = {}

        def _exec(label: str, sql: str) -> None:
            logger.info(f"[ETL-SQL] running: {label}")
            rc = s.execute(text(sql), {"tenant": tenant_id}).rowcount
            stats[label] = rc
            logger.info(f"[ETL-SQL] {label}: {rc}")

        try:
            logger.info(f"[ETL-SQL] Full backfill for tenant {tenant_id}")

            # ETL session: lift the app-level statement timeout and give the
            # planner room for hash joins over ~1.7M rows.
            s.execute(text("SET statement_timeout = 0"))
            s.execute(text("SET work_mem = '256MB'"))

            # Idempotency: wipe this tenant's derived graph
            s.execute(text("DELETE FROM knowledge_edges WHERE tenant_id = :tenant"), {"tenant": tenant_id})
            s.execute(text("DELETE FROM knowledge_embeddings WHERE tenant_id = :tenant"), {"tenant": tenant_id})
            s.execute(text("DELETE FROM knowledge_nodes WHERE tenant_id = :tenant"), {"tenant": tenant_id})

            _exec("contractor_nodes", """
                INSERT INTO knowledge_nodes (id, node_type, external_id, label, description, meta_json, tenant_id, created_at, updated_at)
                SELECT gen_random_uuid(), 'contractor',
                       LEFT(COALESCE(NULLIF(contractor_name, ''), id::text), 255),
                       LEFT(COALESCE(NULLIF(contractor_name, ''), 'Contractor ' || id::text), 500),
                       NULL,
                       json_build_object('contractor_id', id::text,
                                         'total_contracts', COALESCE(total_contracts, 0),
                                         'total_amount_bdt', COALESCE(total_amount_bdt, 0)),
                       :tenant, NOW(), NOW()
                FROM (
                    SELECT DISTINCT ON (LEFT(COALESCE(NULLIF(contractor_name, ''), id::text), 255)) *
                    FROM contractors
                ) c
            """)

            _exec("agency_nodes", """
                INSERT INTO knowledge_nodes (id, node_type, external_id, label, description, meta_json, tenant_id, created_at, updated_at)
                SELECT gen_random_uuid(), 'agency',
                       agency_code, LEFT(agency_name, 500), NULL,
                       json_build_object('agency_id', id::text, 'ministry', ministry),
                       :tenant, NOW(), NOW()
                FROM (SELECT DISTINCT ON (agency_code) * FROM agencies) a
            """)

            _exec("tender_nodes", """
                INSERT INTO knowledge_nodes (id, node_type, external_id, label, description, meta_json, tenant_id, created_at, updated_at)
                SELECT gen_random_uuid(), 'tender',
                       LEFT(package_no, 255),
                       LEFT(COALESCE(NULLIF(title, ''), 'Tender ' || package_no), 500),
                       NULL,
                       json_build_object('agency_code', COALESCE(agency_code, ''),
                                         'procurement_method', COALESCE(procurement_method, '')),
                       :tenant, NOW(), NOW()
                FROM (
                    SELECT DISTINCT ON (LEFT(package_no, 255)) *
                    FROM procurement_tenders
                    WHERE package_no IS NOT NULL AND package_no <> ''
                ) t
            """)

            _exec("award_nodes", """
                INSERT INTO knowledge_nodes (id, node_type, external_id, label, description, meta_json, tenant_id, created_at, updated_at)
                SELECT gen_random_uuid(), 'award',
                       LEFT(COALESCE(package_no, '') || '_' || COALESCE(contractor_name, ''), 255),
                       LEFT('Award ' || COALESCE(contractor_name, ''), 500),
                       title,
                       json_build_object('package_no', COALESCE(package_no, ''),
                                         'contractor', COALESCE(contractor_name, ''),
                                         'amount_bdt', COALESCE(amount_bdt, 0)),
                       :tenant, NOW(), NOW()
                FROM (
                    SELECT DISTINCT ON (LEFT(COALESCE(package_no, '') || '_' || COALESCE(contractor_name, ''), 255)) *
                    FROM award_records_v2
                    WHERE contractor_name IS NOT NULL AND contractor_name <> ''
                ) aw
            """)

            _exec("awarded_to_edges", """
                INSERT INTO knowledge_edges (id, source_node_id, target_node_id, edge_type, weight, meta_json, tenant_id, created_at, updated_at)
                SELECT gen_random_uuid(), c.id, a.id, 'awarded_to', 1.0,
                       json_build_object('amount_bdt', a.meta_json->>'amount_bdt'),
                       :tenant, NOW(), NOW()
                FROM knowledge_nodes a
                JOIN knowledge_nodes c
                  ON c.node_type = 'contractor' AND c.tenant_id = :tenant
                 AND c.external_id = LEFT(a.meta_json->>'contractor', 255)
                WHERE a.node_type = 'award' AND a.tenant_id = :tenant
                  AND COALESCE(a.meta_json->>'contractor', '') <> ''
            """)

            _exec("procured_by_edges", """
                INSERT INTO knowledge_edges (id, source_node_id, target_node_id, edge_type, weight, meta_json, tenant_id, created_at, updated_at)
                SELECT gen_random_uuid(), ag.id, t.id, 'procured_by', 1.0, '{}',
                       :tenant, NOW(), NOW()
                FROM knowledge_nodes t
                JOIN knowledge_nodes ag
                  ON ag.node_type = 'agency' AND ag.tenant_id = :tenant
                 AND ag.external_id = t.meta_json->>'agency_code'
                WHERE t.node_type = 'tender' AND t.tenant_id = :tenant
                  AND COALESCE(t.meta_json->>'agency_code', '') <> ''
            """)

            _exec("award_issued_for_edges", """
                INSERT INTO knowledge_edges (id, source_node_id, target_node_id, edge_type, weight, meta_json, tenant_id, created_at, updated_at)
                SELECT gen_random_uuid(), t.id, a.id, 'award_issued_for', 1.0, '{}',
                       :tenant, NOW(), NOW()
                FROM knowledge_nodes a
                JOIN knowledge_nodes t
                  ON t.node_type = 'tender' AND t.tenant_id = :tenant
                 AND t.external_id = LEFT(a.meta_json->>'package_no', 255)
                WHERE a.node_type = 'award' AND a.tenant_id = :tenant
                  AND COALESCE(a.meta_json->>'package_no', '') <> ''
            """)

            s.commit()
            node_keys = ("contractor_nodes", "agency_nodes", "tender_nodes", "award_nodes")
            edge_keys = ("awarded_to_edges", "procured_by_edges", "award_issued_for_edges")
            summary = {
                "nodes_created": sum(stats[k] for k in node_keys),
                "edges_created": sum(stats[k] for k in edge_keys),
                **stats,
            }
            logger.info(f"[ETL-SQL] Backfill complete: {summary}")
            return summary
        except Exception as e:
            s.rollback()
            logger.error(f"[ETL-SQL] Backfill failed: {e}", exc_info=True)
            raise

    def backfill_all(self, tenant_id: str, skip_embeddings: bool = False) -> Dict[str, int]:
        """Full ETL: contractors → tenders → awards → relationships.

        Returns stats: nodes_created, edges_created.
        """
        stats = {"nodes_created": 0, "edges_created": 0}

        try:
            logger.info(f"[ETL] Starting knowledge graph backfill for tenant {tenant_id}")

            # Fetch each source table ONCE (ordered → deterministic). Node and edge
            # phases must see the same rows or cache keys won't line up.
            tenders = self.session.execute(
                select(ProcurementTender).order_by(ProcurementTender.id).limit(100000)
            ).scalars().all()
            awards = self.session.execute(
                select(AwardRecordV2).order_by(AwardRecordV2.id).limit(100000)
            ).scalars().all()

            # Phase 1: Create contractor nodes
            contractor_ids = self._create_contractor_nodes(tenant_id)
            stats["nodes_created"] += len(contractor_ids)
            logger.info(f"[ETL] Created {len(contractor_ids)} contractor nodes")

            # Phase 2: Create agency nodes
            agency_ids = self._create_agency_nodes(tenant_id)
            stats["nodes_created"] += len(agency_ids)
            logger.info(f"[ETL] Created {len(agency_ids)} agency nodes")

            # Phase 3: Create tender nodes
            tender_ids = self._create_tender_nodes(tenant_id, tenders)
            stats["nodes_created"] += len(tender_ids)
            logger.info(f"[ETL] Created {len(tender_ids)} tender nodes")

            # Phase 4: Create award nodes
            award_ids = self._create_award_nodes(tenant_id, awards)
            stats["nodes_created"] += len(award_ids)
            logger.info(f"[ETL] Created {len(award_ids)} award nodes")

            # Phase 5: Create edges (relationships) — same rows as node phases
            edges_created = 0
            edges_created += self._create_bidder_edges(tenant_id)
            edges_created += self._create_awarded_to_edges(tenant_id, awards)
            edges_created += self._create_procured_by_edges(tenant_id, tenders)
            edges_created += self._create_award_issued_edges(tenant_id, awards)
            stats["edges_created"] = edges_created
            logger.info(f"[ETL] Created {edges_created} edges")

            self.session.commit()
            logger.info(f"[ETL] Knowledge graph backfill complete: {stats}")
            return stats

        except Exception as e:
            self.session.rollback()
            logger.error(f"[ETL] Backfill failed: {e}", exc_info=True)
            raise

    def _create_contractor_nodes(self, tenant_id: str) -> List[UUID]:
        """Create knowledge nodes for all contractors."""
        stmt = select(Contractor).limit(50000)  # batch processing safeguard
        contractors = self.session.execute(stmt).scalars().all()

        node_ids = []
        for contractor in contractors:
            # Keyed by name: awarded_to edges join on award.contractor_name
            ext_id = self._ext(contractor.contractor_name or str(contractor.id))
            node = KnowledgeNode(
                id=str(uuid4()),  # explicit: column default fires at flush, too late for node_cache
                node_type="contractor",
                external_id=ext_id,
                label=(contractor.contractor_name or f"Contractor {contractor.id}")[:500],
                description=None,
                meta_json={
                    "contractor_id": str(contractor.id),
                    "total_contracts": contractor.total_contracts,
                    "total_amount_bdt": float(contractor.total_amount_bdt) if contractor.total_amount_bdt else 0,
                    "agencies_worked": contractor.agencies_worked or [],
                },
                tenant_id=tenant_id,
            )
            self.session.add(node)
            self.node_cache[("contractor", ext_id)] = node.id
            node_ids.append(node.id)

        self.session.flush()
        return node_ids

    def _create_agency_nodes(self, tenant_id: str) -> List[UUID]:
        """Create knowledge nodes for all agencies."""
        stmt = select(Agency).limit(1000)
        agencies = self.session.execute(stmt).scalars().all()

        node_ids = []
        for agency in agencies:
            node = KnowledgeNode(
                id=str(uuid4()),
                node_type="agency",
                external_id=agency.agency_code,
                label=agency.agency_name,
                description=None,
                meta_json={"agency_id": str(agency.id), "ministry": agency.ministry},
                tenant_id=tenant_id,
            )
            self.session.add(node)
            self.node_cache[("agency", agency.agency_code)] = node.id
            node_ids.append(node.id)

        self.session.flush()
        return node_ids

    def _create_tender_nodes(self, tenant_id: str, tenders: List) -> List[UUID]:
        """Create knowledge nodes for the given tenders."""
        node_ids = []
        for tender in tenders:
            label = (tender.title or f"Tender {tender.package_no}")[:500]  # Truncate to 500 chars
            ext_id = self._ext(tender.package_no)
            node = KnowledgeNode(
                id=str(uuid4()),
                node_type="tender",
                external_id=ext_id,
                label=label,
                description=None,
                meta_json={
                    "agency_code": tender.agency_code or "",
                    "procurement_method": tender.procurement_method or "",
                },
                tenant_id=tenant_id,
            )
            self.session.add(node)
            self.node_cache[("tender", ext_id)] = node.id
            node_ids.append(node.id)

        self.session.flush()
        return node_ids

    def _create_award_nodes(self, tenant_id: str, awards: List) -> List[UUID]:
        """Create knowledge nodes for the given awards."""
        node_ids = []
        for award in awards:
            ext_id = self._ext(f"{award.package_no}_{award.contractor_name}")
            node = KnowledgeNode(
                id=str(uuid4()),
                node_type="award",
                external_id=ext_id,
                label=f"Award {award.contractor_name}"[:500],
                description=award.title,
                meta_json={
                    "package_no": award.package_no or "",
                    "contractor": award.contractor_name or "",
                },
                tenant_id=tenant_id,
            )
            self.session.add(node)
            self.node_cache[("award", ext_id)] = node.id
            node_ids.append(node.id)

        self.session.flush()
        return node_ids

    def _create_bidder_edges(self, tenant_id: str) -> int:
        """Contractor bid on tender relationships (inferred from awards)."""
        # Without a separate bidder table, skip this edge type
        # Award records show only winners, not all bidders
        return 0

    def _create_awarded_to_edges(self, tenant_id: str, awards: List) -> int:
        """Contractor awarded contract edges (exact match only)."""
        count = 0
        skipped = 0
        for award in awards:
            if not (award.contractor_name and award.package_no):
                skipped += 1
                continue

            contractor_key = ("contractor", self._ext(award.contractor_name))
            award_key = ("award", self._ext(f"{award.package_no}_{award.contractor_name}"))

            # Only create edge if both nodes exist (exact match)
            if contractor_key in self.node_cache and award_key in self.node_cache:
                edge = KnowledgeEdge(
                    source_node_id=self.node_cache[contractor_key],
                    target_node_id=self.node_cache[award_key],
                    edge_type="awarded_to",
                    weight=1.0,
                    meta_json={},
                    tenant_id=tenant_id,
                )
                self.session.add(edge)
                count += 1
            else:
                skipped += 1

        self.session.flush()
        logger.info(f"[ETL] Created {count} awarded_to edges (skipped {skipped})")
        return count

    def _create_procured_by_edges(self, tenant_id: str, tenders: List) -> int:
        """Agency procured tender edges."""
        count = 0
        skipped = 0
        for tender in tenders:
            # Try to find agency by agency_code
            agency_key = ("agency", tender.agency_code) if tender.agency_code else None
            tender_key = ("tender", self._ext(tender.package_no))

            if not agency_key:
                skipped += 1
                continue

            if agency_key not in self.node_cache or tender_key not in self.node_cache:
                skipped += 1
                continue

            edge = KnowledgeEdge(
                source_node_id=self.node_cache[agency_key],
                target_node_id=self.node_cache[tender_key],
                edge_type="procured_by",
                weight=1.0,
                meta_json={},
                tenant_id=tenant_id,
            )
            self.session.add(edge)
            count += 1

        self.session.flush()
        logger.info(f"[ETL] Created {count} procured_by edges (skipped {skipped})")
        return count

    def _create_award_issued_edges(self, tenant_id: str, awards: List) -> int:
        """Tender issued award edges (skip if nodes missing)."""
        count = 0
        skipped = 0
        for award in awards:
            if not (award.package_no and award.contractor_name):
                skipped += 1
                continue

            tender_key = ("tender", self._ext(award.package_no))
            award_key = ("award", self._ext(f"{award.package_no}_{award.contractor_name}"))

            # Only create edge if both nodes exist
            if tender_key in self.node_cache and award_key in self.node_cache:
                edge = KnowledgeEdge(
                    source_node_id=self.node_cache[tender_key],
                    target_node_id=self.node_cache[award_key],
                    edge_type="award_issued_for",
                    weight=1.0,
                    meta_json={},
                    tenant_id=tenant_id,
                )
                self.session.add(edge)
                count += 1
            else:
                skipped += 1

        self.session.flush()
        logger.info(f"[ETL] Created {count} award_issued_for edges (skipped {skipped})")
        return count


def backfill_knowledge_graph(tenant_id: Optional[str] = None) -> Dict[str, int]:
    """Convenience function to run ETL backfill."""
    engine = get_sync_engine()

    with engine.begin() as conn:
        from sqlalchemy.orm import Session
        session = Session(engine)

        if tenant_id:
            token = set_tenant_context(tenant_id)
        else:
            token = None

        try:
            etl = KnowledgeGraphETL(session)
            # Set-based full-table path (all 998K awards / 727K tenders);
            # backfill_all() remains as the row-by-row ORM fallback.
            stats = etl.backfill_all_sql(tenant_id or "__no_tenant__")
            return stats
        finally:
            if token:
                reset_tenant_context(token)
            session.close()
