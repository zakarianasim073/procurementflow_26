"""Resolve a Works tender estimate by normalized package number with provenance."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import KnowledgeEntry
from app.services.intelligence_base import IntelligenceBaseService


class TenderEstimateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _bdt(value: Any) -> float:
        try:
            amount = float(value or 0)
        except (TypeError, ValueError):
            return 0.0
        # A known legacy APP/NOA source stored values below 10 in crore.
        return amount * 10_000_000 if 0 < amount < 10 else amount

    async def resolve(
        self,
        *,
        tender_id: str,
        package_no: str | None,
        allow_live: bool = False,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        cached = (
            await self.db.execute(
                select(KnowledgeEntry).where(
                    KnowledgeEntry.tender_id == tender_id,
                    KnowledgeEntry.entry_type == "tender_estimate_resolution",
                    KnowledgeEntry.is_archived.is_(False),
                ).order_by(KnowledgeEntry.updated_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        cached_payload = (cached.data or {}).get("payload", {}) if cached else {}
        if cached_payload and (cached_payload.get("amount_bdt", 0) > 0 or not allow_live):
            return cached_payload
        package = IntelligenceBaseService.normalize_package_no(package_no)
        if not package:
            package = await self._find_package(tender_id)
        if not package:
            return {"amount_bdt": 0.0, "source": "unresolved", "confidence": 0.0, "package_no": None}

        candidates: list[dict[str, Any]] = []
        query_specs = [
            ("app_records", "estimated_cost_bdt", "updated_at", 1.0),
            ("procurement_lifecycle", "estimated_cost_bdt", "updated_at", 0.98),
            ("canonical_tenders", "estimated_cost_bdt", "rebuilt_at", 0.96),
            ("award_records_v2", "estimated_amount_bdt", "updated_at", 0.9),
        ]
        for table, column, order_column, confidence in query_specs:
            # APP has a maintained, indexed normalized key. Other sources use
            # their indexed package_no for the fast exact path; applying regex
            # to every row caused 40-50 second workspace loads on misses.
            package_condition = (
                "normalized_package_no = :package"
                if table == "app_records"
                else "package_no = :package"
            )
            row = (
                await self.db.execute(
                    text(
                        f"SELECT {column} AS amount, package_no FROM {table} "
                        f"WHERE {package_condition} AND COALESCE({column}, 0) > 0 "
                        f"ORDER BY {order_column} DESC NULLS LAST LIMIT 1"
                    ),
                    {"package": package},
                )
            ).mappings().first()
            if row:
                candidates.append({
                    "amount_bdt": self._bdt(row["amount"]),
                    "source": table,
                    "confidence": confidence,
                    "package_no": row["package_no"] or package,
                })

        if not candidates:
            candidates.extend(await self._fuzzy_app_candidates(tender_id, package))
        resolution = dict(candidates[0]) if candidates and candidates[0]["confidence"] >= 0.86 else None
        if resolution is None and allow_live:
            resolution = await self._live_app_lookup(tender_id, package)

        if resolution is None:
            resolution = {"amount_bdt": 0.0, "source": "unresolved", "confidence": 0.0,
                          "package_no": package, "status": "review_required" if candidates else "unresolved"}
        else:
            resolution["status"] = "resolved"
        resolution["candidates"] = candidates[:10]
        resolution["resolved_at"] = datetime.now(timezone.utc).isoformat()
        await self._persist(tender_id, resolution, tenant_id)
        return resolution

    async def _fuzzy_app_candidates(self, tender_id: str, package: str) -> list[dict[str, Any]]:
        """Recover APP candidates by package/title/PE similarity without silently accepting weak matches."""
        source = (await self.db.execute(text("""
            SELECT title, pe_office, agency_code, package_no
            FROM pf_tenders WHERE tender_id=:tid OR package_no=:tid
            ORDER BY updated_at DESC NULLS LAST LIMIT 1
        """), {"tid": tender_id})).mappings().first()
        if not source:
            return []
        rows = (await self.db.execute(text("""
            SELECT id, package_no, title, pe_office, agency_code, financial_year,
                   estimated_cost_bdt,
                   GREATEST(similarity(normalized_package_no, :package),
                            similarity(COALESCE(title,''), :title)) AS score,
                   similarity(COALESCE(pe_office,''), :pe) AS pe_score
            FROM app_records
            WHERE estimated_cost_bdt > 0 AND category='Works'
              AND (agency_code=:agency OR similarity(COALESCE(title,''), :title) > 0.38
                   OR similarity(normalized_package_no, :package) > 0.35)
            ORDER BY score DESC, pe_score DESC, updated_at DESC NULLS LAST LIMIT 10
        """), {"package": package, "title": source["title"] or "", "pe": source["pe_office"] or "",
               "agency": source["agency_code"]})).mappings().all()
        candidates = []
        for row in rows:
            confidence = min(0.95, float(row["score"] or 0) * 0.72 + float(row["pe_score"] or 0) * 0.18
                             + (0.08 if row["agency_code"] == source["agency_code"] else 0))
            candidates.append({
                "amount_bdt": self._bdt(row["estimated_cost_bdt"]), "source": "app_records_fuzzy",
                "source_record_id": str(row["id"]), "confidence": round(confidence, 3),
                "package_no": row["package_no"], "title": row["title"],
                "pe_office": row["pe_office"], "financial_year": row["financial_year"],
                "match_method": "package_title_pe_agency_similarity",
                "match_evidence": {
                    "package_or_title_similarity": round(float(row["score"] or 0), 3),
                    "pe_office_similarity": round(float(row["pe_score"] or 0), 3),
                    "agency_match": row["agency_code"] == source["agency_code"],
                },
            })
        return candidates

    async def _find_package(self, tender_id: str) -> str:
        for table in ("pf_tenders", "procurement_lifecycle", "canonical_tenders"):
            row = (
                await self.db.execute(
                    text(f"SELECT package_no FROM {table} WHERE tender_id = :tid LIMIT 1"),
                    {"tid": tender_id},
                )
            ).scalar_one_or_none()
            package = IntelligenceBaseService.normalize_package_no(row)
            if package:
                return package
        return ""

    async def _live_app_lookup(self, tender_id: str, package: str) -> dict[str, Any] | None:
        from app.agents.egp_client import EGPClient
        from app.services.app_noa_service import APPNOAMatchingService

        client = EGPClient()
        rows = await asyncio.to_thread(client.search_app, package)
        match = next(
            (
                item for item in rows
                if IntelligenceBaseService.normalize_package_no(item.get("package_no")) == package
            ),
            None,
        )
        if not match:
            return None
        amount = self._bdt(match.get("estimated_amount_bdt") or match.get("estimated_cost"))
        if amount <= 0:
            return None

        # The workspace is Works-only; persist the exact matched APP record so
        # future reads resolve from PG17 without another portal request.
        payload = {
            **match,
            "package_no": match.get("package_no") or package,
            "estimated_cost": amount,
            "category": "Works",
            "source": "egp_live_app",
        }
        service = APPNOAMatchingService(self.db)
        async with self.db.begin_nested():
            await service.ingest_app_plan_record(payload)
        await self.db.flush()
        return {
            "amount_bdt": amount,
            "source": "egp_live_app",
            "confidence": 1.0,
            "package_no": payload["package_no"],
            "tender_id": tender_id,
        }

    async def _persist(self, tender_id: str, resolution: dict[str, Any], tenant_id: str | None) -> None:
        existing = (
            await self.db.execute(
                select(KnowledgeEntry)
                .where(
                    KnowledgeEntry.tender_id == tender_id,
                    KnowledgeEntry.entry_type == "tender_estimate_resolution",
                    KnowledgeEntry.is_archived.is_(False),
                )
                .order_by(KnowledgeEntry.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        checksum = hashlib.sha256(json.dumps(resolution, sort_keys=True, default=str).encode()).hexdigest()
        if existing:
            existing.data = {"payload": resolution}
            existing.summary = f"Estimated cost resolved from {resolution['source']}"
            existing.checksum = checksum
        else:
            self.db.add(KnowledgeEntry(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                tender_id=tender_id,
                entry_type="tender_estimate_resolution",
                title=f"Tender estimate {tender_id}",
                summary=f"Estimated cost resolved from {resolution['source']}",
                source="tender_estimate_service",
                data={"payload": resolution},
                checksum=checksum,
                tags={"works_only": True, "package_match": True},
            ))
        await self.db.flush()
