"""ContractorService â€“ domain service extracted from IntelligenceDataService monolith."""
from __future__ import annotations

import json
import logging
import os
import re
from html import unescape
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from sqlalchemy import and_, case, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agency_extractor import extract_agency_with_confidence
from app.services.intelligence_base import IntelligenceBaseService

logger = logging.getLogger(__name__)

CONTRACTOR_EXCLUSION_PATTERNS = [
    re.compile(r"\bjv\b", re.IGNORECASE),
    re.compile(r"\bjoint venture\b", re.IGNORECASE),
    re.compile(r"\bconsortium\b", re.IGNORECASE),
]
MIN_CREDIBLE_NPP = 0.05
MAX_CREDIBLE_NPP = 1.5
MIN_CREDIBLE_ESTIMATE_BDT = 1000.0
MIN_CREDIBLE_AWARD_BDT = 1000.0
RUNTIME_DIR = Path(__file__).resolve().parent.parent.parent / "runtime"

@dataclass
class ImportProgress:
    """Mutable progress tracker shared between the service and the status endpoint."""
    state: str = "queued"
    started: bool = False
    current_phase: str = "waiting"
    current_file: str = ""
    files_completed: int = 0
    files_total: int = 0
    current_file_records: int = 0
    current_file_imported: int = 0
    records_committed: int = 0
    records: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    summary: Optional[Dict[str, int]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        pct = (self.files_completed / self.files_total * 100) if self.files_total > 0 else 0
        return {
            "state": self.state,
            "started": self.started,
            "current_phase": self.current_phase,
            "current_file": self.current_file,
            "files_completed": self.files_completed,
            "files_total": self.files_total,
            "progress_pct": round(pct, 1),
            "current_file_records": self.current_file_records,
            "current_file_imported": self.current_file_imported,
            "records_committed": self.records_committed,
            "records": dict(self.records),
            "summary": self.summary,
            "error": self.error,
        }


class ContractorService(IntelligenceBaseService):
    """Domain service for contractor operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.db = db
        self._batch_size = max(int(os.getenv("INTEL_IMPORT_BATCH_SIZE", "500")), 50)

    @staticmethod
    def _coalesce(*values: Any) -> Any:
        for value in values:
            if value not in (None, "", [], {}):
                return value
        return None
    async def _commit_import_batch(
        self,
        progress: Optional[ImportProgress],
        processed_total: int,
        imported_total: int,
        committed_now: int,
    ) -> None:
        await self.db.flush()
        await self.db.commit()
        if progress:
            progress.current_file_records = processed_total
            progress.current_file_imported = imported_total
            progress.records_committed += committed_now
    def _contractor_match_score(self, query_norm: str, candidate_name: Any, contractor_id: Any = None) -> int:
        """Score contractor candidates by exactness, token overlap, and fuzzy similarity."""
        candidate_norm = self._normalize_search_text(candidate_name)
        if not query_norm or not candidate_norm:
            return 0

        if contractor_id and str(contractor_id).strip().upper() == query_norm:
            return 1000
        if candidate_norm == query_norm:
            return 900

        candidate_tokens = set(candidate_norm.split())
        query_tokens = set(query_norm.split())
        overlap = len(candidate_tokens & query_tokens)
        score = overlap * 20

        if query_norm in candidate_norm:
            score += 60
        if candidate_norm in query_norm:
            score += 30

        ratio = SequenceMatcher(None, candidate_norm, query_norm).ratio()
        score += int(ratio * 100)
        return score
    async def _ensure_contractor_cache(self) -> Dict[str, Any]:
        from app.models.intelligence import Contractor

        if self._contractor_cache is None:
            self._contractor_cache = {
                row.contractor_name: row
                for row in (await self.db.execute(select(Contractor))).scalars().all()
            }
        return self._contractor_cache
    async def _ensure_eexperience_schema(self) -> None:
        """Ensure eexperience schema columns exist.

        .. deprecated::
            These ALTER TABLE statements should be moved to Alembic migration 006+.
            Runtime DDL causes schema drift invisible to `alembic revision --autogenerate`.
            This method is kept for backward compatibility on fresh deployments
            that pre-date the migration.  Once migration 006 covers these columns,
            this method should become a no-op.
        """
        if self._eexperience_schema_ready:
            return
        # Quick schema probe: skip if one representative column already exists
        probe = await self.db.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'econtract_execution' AND column_name = 'completed_value_bdt'"
            )
        )
        if probe.scalar_one_or_none():
            self._eexperience_schema_ready = True
            return
        ddl = [
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS completed_value_bdt DOUBLE PRECISION DEFAULT 0",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS planned_completion_date VARCHAR(20)",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS actual_completion_date VARCHAR(20)",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS completion_status VARCHAR(50)",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS work_status VARCHAR(100)",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS progress_pct DOUBLE PRECISION DEFAULT 0",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS delay_days INTEGER DEFAULT 0",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS extension_days INTEGER DEFAULT 0",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS completed_on_time BOOLEAN",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS performance_rating VARCHAR(50)",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS completion_certificate_no VARCHAR(200)",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS bill_no VARCHAR(200)",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS fiscal_year VARCHAR(20)",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS remarks TEXT",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS raw_payload JSON",
            "ALTER TABLE econtract_execution ADD COLUMN IF NOT EXISTS data_source VARCHAR(50)",
        ]
        for table in ("eexperience_completed", "ecms_ongoing"):
            ddl.extend([
                # sql-ok-block(17): table from hardcoded tuple (DDL bootstrap)
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tender_ref_no VARCHAR(300)",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS package_name TEXT",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS name_of_work TEXT",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS ministry_division VARCHAR(300)",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS organization_name VARCHAR(300)",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS pe_name VARCHAR(300)",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS procurement_nature VARCHAR(100)",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS work_category VARCHAR(200)",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS contract_no VARCHAR(200)",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS physical_progress_pct DOUBLE PRECISION DEFAULT 0",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS financial_progress_pct DOUBLE PRECISION DEFAULT 0",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS physical_progress_date VARCHAR(20)",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS financial_progress_date VARCHAR(20)",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS is_jvca BOOLEAN",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS remarks TEXT",
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS comments_by_pe TEXT",
                f"CREATE INDEX IF NOT EXISTS ix_{table}_tender_package ON {table} (tender_id, package_no)",
            ])
        for stmt in ddl:
            await self.db.execute(text(stmt))
        # Backfill data_source from raw_payload for records that have it
        backfill = (
            "UPDATE econtract_execution SET data_source = raw_payload->>'source' "
            "WHERE data_source IS NULL AND raw_payload IS NOT NULL "
            "AND raw_payload->>'source' IS NOT NULL"
        )
        await self.db.execute(text(backfill))
        # Set default for remaining nulls
        await self.db.execute(text(
            "UPDATE econtract_execution SET data_source = 'EEXPERIENCE' WHERE data_source IS NULL OR data_source = ''"
        ))
        await self.db.commit()
        self._eexperience_schema_ready = True
    def _is_credible_npp_row(cls, row: Any) -> bool:
        npp = cls._safe_float(getattr(row, "npp_ratio", 0))
        estimate = cls._safe_float(getattr(row, "estimated_cost_bdt", 0))
        award = cls._safe_float(getattr(row, "award_amount_bdt", 0))
        match_type = str(getattr(row, "match_type", "") or "")
        data_source = str(getattr(row, "data_source", "") or "")
        if match_type not in ("package_exact", "title_similarity"):
            return False
        if data_source != "matched":
            return False
        if estimate < MIN_CREDIBLE_ESTIMATE_BDT or award < MIN_CREDIBLE_AWARD_BDT:
            return False
        return MIN_CREDIBLE_NPP <= npp <= MAX_CREDIBLE_NPP
    @staticmethod
    def _normalize_search_text(value: Any) -> str:
        """Normalize contractor text for fuzzy search and matching."""
        raw = unescape(str(value or "")).strip().upper()
        if not raw:
            return ""
        raw = raw.replace("&AMP;", "&")
        raw = re.sub(r"\b(M/S|M\.S\.|MESSRS|MS)\b", " ", raw)
        raw = re.sub(r"[^A-Z0-9]+", " ", raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        return raw
    @staticmethod
    def _normalize_spaces(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()
    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        if row is None:
            return {}
        payload: Dict[str, Any] = {}
        for col in row.__table__.columns:
            val = getattr(row, col.name)
            if isinstance(val, datetime):
                val = val.isoformat()
            payload[col.name] = val
        return payload
    @staticmethod
    def _safe_float(value: Any) -> float:
        if value in (None, ""):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        raw = str(value).replace(",", "").strip()
        raw = raw.replace("BDT", "").replace("TK", "").strip()
        try:
            return float(raw)
        except ValueError:
            m = re.search(r"-?\d+(?:\.\d+)?", raw)
            return float(m.group(0)) if m else 0.0
    @staticmethod
    def _safe_int(value: Any) -> int:
        if value in (None, ""):
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(round(value))
        raw = str(value).strip()
        if not raw:
            return 0
        match = re.search(r"-?\d+", raw.replace(",", ""))
        return int(match.group(0)) if match else 0
    def _should_exclude_contractor_name(cls, value: Any) -> bool:
        name = cls._normalize_spaces(value)
        if not name:
            return True
        upper = name.upper()
        if len(name) < 5:
            return True
        if len(re.sub(r"[^A-Za-z]", "", name)) < 4:
            return True
        if "JV" in re.sub(r"[^A-Z]", "", upper):
            return True
        if any(pattern.search(name) for pattern in CONTRACTOR_EXCLUSION_PATTERNS):
            return True
        noise_markers = ("UNKNOWN", "N/A", "TEST", "DUMMY", "NOT AVAILABLE")
        if any(marker in upper for marker in noise_markers):
            return True
        return False
    @staticmethod
    def _to_iso_date(value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        raw = str(value).strip()
        if not raw:
            return None
        raw = raw.replace("Z", "+00:00")
        for fmt in (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d-%b-%Y",
            "%d-%b-%Y %H:%M",
            "%d-%b-%Y %H:%M:%S",
            "%d %b %Y",
        ):
            try:
                return datetime.strptime(raw[:19], fmt).date().isoformat()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(raw).date().isoformat()
        except ValueError:
            return raw[:10]
    @staticmethod
    def _uuid() -> str:
        return str(uuid4())
    async def benchmark_contractor(self, contractor_id: str, agency: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Compare a contractor against peers (same agency or all)."""
        from app.models.intelligence import Contractor, ContractorDNA

        contractor = await self.db.get(Contractor, contractor_id)
        if not contractor:
            return None
        dna = await self.get_contractor_dna(contractor_id)
        if not dna:
            return None

        # Peer group: contractors in the same agency
        if not agency and dna.get("preferred_agency"):
            agency = dna["preferred_agency"]

        peers_query = select(ContractorDNA)
        if agency:
            peers_query = peers_query.where(ContractorDNA.preferred_agency == agency)
        peers = (await self.db.execute(peers_query)).scalars().all()

        if not peers:
            return {"contractor": dna, "peers": [], "percentiles": {}, "verdict": "No peer data"}

        # Compute percentiles for key metrics
        metrics = [
            ("health_score", "higher"),
            ("completion_rate", "higher"),
            ("on_time_rate", "higher"),
            ("avg_discount_pct", "higher"),
            ("total_amount_bdt", "higher"),
            ("total_contracts", "higher"),
            ("avg_npp", "lower"),
            ("npp_volatility", "lower"),
            ("avg_delay_days", "lower"),
        ]
        percentiles = {}
        strengths = []
        weaknesses = []
        for metric, direction in metrics:
            vals = sorted([getattr(p, metric, 0) for p in peers])
            contractor_val = dna.get(metric, 0)
            if not vals or vals[-1] == vals[0]:
                percentile = 50.0
            else:
                count_below = sum(1 for v in vals if v <= contractor_val)
                percentile = round((count_below / len(vals)) * 100, 1)
            percentiles[metric] = {
                "value": contractor_val,
                "percentile": percentile,
                "peer_min": min(vals),
                "peer_max": max(vals),
                "peer_avg": round(sum(vals) / len(vals), 4),
            }
            if direction == "higher":
                if percentile >= 80:
                    strengths.append(metric)
                elif percentile <= 20:
                    weaknesses.append(metric)
            else:
                if percentile <= 20:
                    strengths.append(metric)
                elif percentile >= 80:
                    weaknesses.append(metric)

        return {
            "contractor": dna,
            "peer_count": len(peers),
            "peer_agency": agency,
            "percentiles": percentiles,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }
    async def get_contractor(self, name_or_id: str) -> Optional[Dict[str, Any]]:
        from app.models.intelligence import Contractor

        query_norm = self._normalize_search_text(name_or_id)
        result = await self.db.execute(
            select(Contractor).where(
                or_(
                    Contractor.contractor_name.ilike(f"%{name_or_id}%"),
                    Contractor.contractor_name.ilike(f"%{query_norm}%"),
                    Contractor.id == name_or_id,
                )
            )
        )
        rows = result.scalars().all()
        if rows:
            ranked = sorted(
                (
                    row
                    for row in rows
                    if not self._should_exclude_contractor_name(row.contractor_name)
                ),
                key=lambda row: self._contractor_match_score(query_norm, row.contractor_name, getattr(row, "id", None)),
                reverse=True,
            )
            if ranked:
                return self._row_to_dict(ranked[0])

        fallback = await self.search_contractors(name_or_id, limit=1)
        return fallback[0] if fallback else None
    async def get_contractor_dna(self, contractor_id: str) -> Optional[Dict[str, Any]]:
        from app.models.intelligence import ContractorDNA

        result = await self.db.execute(
            select(ContractorDNA).where(ContractorDNA.contractor_id == contractor_id)
        )
        row = result.scalar_one_or_none()
        return self._row_to_dict(row) if row else None
    async def get_contractor_performance(
        self,
        contractor_name: str,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.models.intelligence import EContractExecution as EE

        await self._ensure_eexperience_schema()
        conditions = [EE.contractor_name.ilike(f"%{contractor_name}%")]
        if source:
            conditions.append(EE.data_source == source)
        where = and_(*conditions)

        total = await self.db.scalar(select(func.count(EE.id)).where(where))
        total_val = await self.db.scalar(select(func.coalesce(func.sum(EE.contract_value_bdt), 0)).where(where))
        completed_val = await self.db.scalar(select(func.coalesce(func.sum(EE.completed_value_bdt), 0)).where(where))

        # Completion rate
        completed_count = await self.db.scalar(
            select(func.count(EE.id)).where(and_(
                where,
                or_(EE.actual_completion_date.is_not(None), EE.completion_status.ilike("%complete%"), EE.status.ilike("%complete%"))
            ))
        )
        completion_rate = round((completed_count or 0) / max(total or 1, 1) * 100, 2)

        # On-time rate
        on_time_count = await self.db.scalar(
            select(func.count(EE.id)).where(and_(where, EE.completed_on_time.is_(True)))
        )
        on_time_rate = round((on_time_count or 0) / max(completed_count or 1, 1) * 100, 2)

        # Avg delay
        avg_delay = await self.db.scalar(select(func.coalesce(func.avg(EE.delay_days), 0)).where(and_(where, EE.delay_days > 0)))

        # Agencies worked with
        agencies_q = await self.db.execute(
            select(EE.agency_code, func.count(EE.id).label("cnt"))
            .where(and_(where, EE.agency_code.is_not(None)))
            .group_by(EE.agency_code)
            .order_by(func.count(EE.id).desc())
            .limit(10)
        )
        agencies = [{"agency_code": r[0], "contracts": int(r[1])} for r in agencies_q.all()]

        # Recent contracts
        recent_q = await self.db.execute(
            select(EE).where(where)
            .order_by(EE.contract_start_date.desc().nullslast())
            .limit(10)
        )
        recent = [self._row_to_dict(r) for r in recent_q.scalars().all()]

        # Value range
        min_v = await self.db.scalar(select(func.min(EE.contract_value_bdt)).where(where))
        max_v = await self.db.scalar(select(func.max(EE.contract_value_bdt)).where(where))

        return {
            "contractor_name": contractor_name,
            "total_contracts": int(total or 0),
            "total_value_bdt": round(float(total_val or 0), 2),
            "completed_value_bdt": round(float(completed_val or 0), 2),
            "completion_rate_pct": completion_rate,
            "on_time_rate_pct": on_time_rate,
            "avg_delay_days": round(float(avg_delay or 0), 1),
            "min_contract_value_bdt": round(float(min_v or 0), 2),
            "max_contract_value_bdt": round(float(max_v or 0), 2),
            "agencies": agencies,
            "recent_contracts": recent,
        }
    async def get_contractor_stats(self) -> Dict[str, Any]:
        from app.models.intelligence import Contractor

        total, total_amount, avg_npp = (
            await self.db.execute(
                select(
                    func.count(Contractor.id),
                    func.coalesce(func.sum(Contractor.total_amount_bdt), 0),
                    func.coalesce(func.avg(Contractor.avg_npp), 0),
                )
            )
        ).one()
        return {
            "total_contractors": total or 0,
            "total_amount_bdt": round(float(total_amount or 0), 2),
            "avg_npp": round(float(avg_npp or 0), 4),
        }
    async def import_contractors_from_json(self, json_path: Optional[Path] = None, progress: Optional[ImportProgress] = None) -> int:
        from app.models.intelligence import Contractor

        fp = json_path or (RUNTIME_DIR / "knowledge" / "contractordna" / "contractors.json")
        if not fp.exists():
            return 0
        payload = json.loads(fp.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            if "contractors" in payload:
                records = payload["contractors"]
            elif "contractor_name" in payload:
                records = [payload]
            else:
                records = []
        else:
            records = payload
        imported = 0
        processed = 0
        ops_since_commit = 0
        contractor_cache = await self._ensure_contractor_cache()
        for item in records:
            if not isinstance(item, dict):
                continue
            name = (item.get("contractor_name") or "").strip()
            if not name:
                continue
            existing = contractor_cache.get(name)
            total_contracts = self._safe_int(self._coalesce(item.get("total_contracts"), item.get("total_wins")))
            total_amount = self._safe_float(item.get("total_amount_bdt"))
            agencies = item.get("agencies") or []
            districts = item.get("districts") or []
            years_active = item.get("years_active") or []
            avg_npp = self._safe_float(
                self._coalesce(item.get("avg_npp"), (self._safe_float(item.get("avg_discount_percent")) / 100.0 if item.get("avg_discount_percent") is not None else None))
            )
            first_award = self._to_iso_date(item.get("earliest_contract_date"))
            last_award = self._to_iso_date(item.get("latest_contract_date"))
            if not first_award and years_active:
                first_award = str(min(years_active))
            if not last_award and years_active:
                last_award = str(max(years_active))

            if existing is None:
                contractor = Contractor(
                    id=self._uuid(),
                    contractor_name=name,
                    total_contracts=total_contracts,
                    total_amount_bdt=total_amount,
                    agencies_worked=agencies,
                    districts_worked=districts,
                    avg_npp=avg_npp,
                    first_award_date=first_award,
                    last_award_date=last_award,
                )
                self.db.add(contractor)
                contractor_cache[name] = contractor
                imported += 1
            else:
                existing.total_contracts = max(existing.total_contracts or 0, total_contracts)
                existing.total_amount_bdt = max(existing.total_amount_bdt or 0.0, total_amount)
                existing.agencies_worked = agencies or existing.agencies_worked
                existing.districts_worked = districts or existing.districts_worked
                existing.avg_npp = avg_npp or existing.avg_npp
                existing.first_award_date = existing.first_award_date or first_award
                existing.last_award_date = existing.last_award_date or last_award
            processed += 1
            ops_since_commit += 1
            if progress:
                progress.current_file_records = processed
                progress.current_file_imported = imported
            if ops_since_commit >= self._batch_size:
                await self._commit_import_batch(progress, processed, imported, ops_since_commit)
                ops_since_commit = 0
        if ops_since_commit:
            await self._commit_import_batch(progress, processed, imported, ops_since_commit)
        else:
            await self.db.flush()
        return imported
    async def list_contractors(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        from app.models.intelligence import Contractor

        result = await self.db.execute(
            select(Contractor)
            .order_by(Contractor.total_amount_bdt.desc(), Contractor.contractor_name.asc())
            .limit(max(limit * 3, 100))
            .offset(offset)
        )
        records = [self._row_to_dict(r) for r in result.scalars().all()]
        filtered = [r for r in records if not self._should_exclude_contractor_name(r.get("contractor_name"))]
        return filtered[:limit]
    async def rebuild_contractor_intelligence(self) -> Dict[str, int]:
        from app.services.contractor_dna_service import ContractorDNAService

        result = await ContractorDNAService(self.db).rebuild_contractor_intelligence()
        return {
            "contractors_updated": int(result.get("rebuilt", 0) or 0),
            "contractor_dna_v2": int(result.get("rebuilt_v2", 0) or 0),
        }

        from app.models.intelligence import Contractor, ContractorDNA, EContractExecution, ProcurementLifecycle

        await self.db.execute(text("TRUNCATE TABLE contractor_dna"))
        await self.db.flush()
        awards = (
            await self.db.execute(
                select(ProcurementLifecycle).where(ProcurementLifecycle.winner.is_not(None))
            )
        ).scalars().all()
        grouped: Dict[str, list] = defaultdict(list)
        for row in awards:
            grouped[row.winner].append(row)

        existing_contractors = {
            row.contractor_name: row
            for row in (await self.db.execute(select(Contractor))).scalars().all()
        }

        # Gather eExperience execution stats per contractor
        await self._ensure_eexperience_schema()
        exec_rows = (await self.db.execute(select(EContractExecution))).scalars().all()
        exec_by_contractor: Dict[str, list] = defaultdict(list)
        for er in exec_rows:
            if er.contractor_name:
                exec_by_contractor[er.contractor_name].append(er)

        contractors_updated = 0
        for name, rows in grouped.items():
            total_amount = sum(self._safe_float(r.award_amount_bdt) for r in rows)
            total_contracts = len(rows)
            agencies = sorted({r.agency_code for r in rows if r.agency_code})
            zones = sorted({r.zone_name for r in rows if r.zone_name})
            npps = [self._safe_float(r.npp_ratio) for r in rows if self._is_credible_npp_row(r)]
            avg_npp = round(sum(npps) / len(npps), 6) if npps else 0.0
            first_award = min((r.award_date for r in rows if r.award_date), default=None)
            last_award = max((r.award_date for r in rows if r.award_date), default=None)
            preferred_agency = max(agencies, key=lambda ag: sum(1 for r in rows if r.agency_code == ag)) if agencies else None
            preferred_zone = max(zones, key=lambda zn: sum(1 for r in rows if r.zone_name == zn)) if zones else None
            avg_award = round(total_amount / total_contracts, 2) if total_contracts else 0.0
            volatility = 0.0
            if len(npps) > 1:
                mean = sum(npps) / len(npps)
                volatility = (sum((v - mean) ** 2 for v in npps) / len(npps)) ** 0.5

            # eExperience performance enrichment
            erows = exec_by_contractor.get(name, [])
            total_exp_contracts = len(erows)
            total_exp_value = sum(self._safe_float(r.contract_value_bdt) for r in erows)
            completed_count = sum(
                1 for r in erows
                if r.actual_completion_date or (r.completion_status and "complete" in r.completion_status.lower())
                or (r.status and "complete" in r.status.lower())
            )
            on_time_count = sum(1 for r in erows if r.completed_on_time is True)
            delays = [r.delay_days for r in erows if r.delay_days and r.delay_days > 0]
            completion_rate = round((completed_count / max(total_exp_contracts, 1)) * 100, 2) if total_exp_contracts else 0.0
            on_time_rate = round((on_time_count / max(completed_count, 1)) * 100, 2) if completed_count else 0.0
            avg_delay = round(sum(delays) / len(delays), 1) if delays else 0.0

            contractor = existing_contractors.get(name)
            if contractor is None:
                contractor = Contractor(id=self._uuid(), contractor_name=name)
                self.db.add(contractor)
                await self.db.flush()
                existing_contractors[name] = contractor
            contractor.total_contracts = total_contracts
            contractor.total_amount_bdt = total_amount
            contractor.agencies_worked = agencies
            contractor.districts_worked = zones
            contractor.avg_npp = avg_npp
            contractor.first_award_date = first_award
            contractor.last_award_date = last_award

            # Health score = composite of execution quality + pricing + scale
            completion_norm = completion_rate / 100.0
            on_time_norm = on_time_rate / 100.0
            delay_penalty = max(0.0, 1.0 - (avg_delay / 365.0)) if avg_delay > 0 else 1.0
            npp_score = max(0.0, 1.0 - (avg_npp / 0.30)) if avg_npp else 0.5  # lower NPP = better
            diversity_score = min(1.0, (len(agencies) * 0.1 + len(zones) * 0.05))
            health_score = round(
                completion_norm * 0.30
                + on_time_norm * 0.25
                + delay_penalty * 0.15
                + npp_score * 0.15
                + diversity_score * 0.15,
                4,
            )

            self.db.add(
                ContractorDNA(
                    id=self._uuid(),
                    contractor_id=contractor.id,
                    total_contracts=total_contracts,
                    total_amount_bdt=total_amount,
                    avg_award_bdt=avg_award,
                    agencies_worked=len(agencies),
                    districts_worked=len(zones),
                    preferred_agency=preferred_agency,
                    preferred_zone=preferred_zone,
                    avg_npp=avg_npp,
                    npp_volatility=volatility,
                    win_rate=0.0,
                    avg_discount_pct=max(0.0, round((1 - avg_npp) * 100, 4)) if avg_npp else 0.0,
                    first_award_date=first_award,
                    last_award_date=last_award,
                    completion_rate=completion_rate,
                    on_time_rate=on_time_rate,
                    avg_delay_days=avg_delay,
                    total_experience_contracts=total_exp_contracts,
                    total_experience_value_bdt=round(total_exp_value, 2),
                    health_score=health_score,
                )
            )
            contractors_updated += 1

        await self.db.flush()
        return {"contractors_updated": contractors_updated}
    async def search_contractors(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        from app.models.intelligence import Contractor

        query_norm = self._normalize_search_text(query)
        if not query_norm:
            return []
        tokens = [token for token in query_norm.split() if len(token) >= 2]

        stmt = select(Contractor)
        if tokens:
            token_filters = [Contractor.contractor_name.ilike(f"%{token}%") for token in tokens[:5]]
            stmt = stmt.where(or_(*token_filters))
        stmt = stmt.order_by(Contractor.total_amount_bdt.desc(), Contractor.contractor_name.asc()).limit(max(limit * 10, 100))

        result = await self.db.execute(
            stmt
        )
        rows = [
            r
            for r in result.scalars().all()
            if not self._should_exclude_contractor_name(r.contractor_name)
        ]
        ranked = sorted(
            rows,
            key=lambda row: (
                self._contractor_match_score(query_norm, row.contractor_name, getattr(row, "id", None)),
                self._safe_float(getattr(row, "total_amount_bdt", 0)),
            ),
            reverse=True,
        )
        return [self._row_to_dict(r) for r in ranked[:limit]]
