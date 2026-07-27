"""DashboardService â€“ domain service extracted from IntelligenceDataService monolith."""
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

# TTL cache for expensive overview queries (5 minutes)
import time as _time
_overview_cache: Dict[str, Any] = {}
_OVERVIEW_CACHE_TTL = 300

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


class DashboardService(IntelligenceBaseService):
    """Domain service for dashboard operations."""
    _agency_cache: Optional[List[Dict[str, str]]] = None
    _department_tree_cache: Optional[List[Dict[str, Any]]] = None

    def __init__(self, db: AsyncSession):
        self.db = db
        self._batch_size = max(int(os.getenv("INTEL_IMPORT_BATCH_SIZE", "500")), 50)
        self._eexperience_schema_ready = False
        from app.services.app_noa_service import APPNOAMatchingService

        self._app_noa = APPNOAMatchingService(db)

    def _build_execution_where(
        self,
        model,
        agency: Optional[str] = None,
        contractor: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ):
        conds = []
        if agency:
            conds.append(or_(model.agency_code.ilike(f"%{agency}%"), model.pe_office.ilike(f"%{agency}%")))
        if contractor:
            conds.append(model.contractor_name.ilike(f"%{contractor}%"))
        if date_from:
            conds.append(model.contract_start_date >= date_from)
        if date_to:
            conds.append(model.contract_start_date <= date_to)
        return and_(*conds) if conds else text("1=1")
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
    async def _guess_agency_code(self, text_value: str) -> Optional[str]:
        raw = (text_value or "").strip()
        if not raw:
            return None
        upper = raw.upper()
        for agency in await self._load_agency_cache():
            keyword = (agency.get("keyword") or agency.get("agency_code") or "").upper()
            name = (agency.get("agency_name") or "").upper()
            if keyword and keyword in upper:
                return agency.get("agency_code") or None
            if name and name in upper:
                return agency.get("agency_code") or None
            agency_code = (agency.get("agency_code") or "").upper()
            if agency_code and agency_code in upper:
                return agency.get("agency_code") or None
        return self._guess_agency_code_from_keywords(raw)
    @staticmethod
    def _guess_agency_code_from_keywords(text_value: str) -> Optional[str]:
        upper = (text_value or "").upper()
        keyword_map = {
            "LGED": ("LGED", "LOCAL GOVERNMENT ENGINEERING"),
            "PWD": ("PWD", "PUBLIC WORKS"),
            "BWDB": ("BWDB", "BANGLADESH WATER DEVELOPMENT"),
            "RHD": ("RHD", "ROADS AND HIGHWAYS"),
            "DPHE": ("DPHE", "PUBLIC HEALTH ENGINEERING"),
            "BREB": ("BREB", "RURAL ELECTRIFICATION"),
            "BADC": ("BADC", "AGRICULTURAL DEVELOPMENT"),
        }
        for agency_code, markers in keyword_map.items():
            if any(marker in upper for marker in markers):
                return agency_code
        agency, confidence = extract_agency_with_confidence(text_value)
        return agency if confidence > 0 else None
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
    def _is_valid_eexperience_record(cls, item: Dict[str, Any]) -> bool:
        title = cls._normalize_spaces(item.get("title"))
        pe_office = cls._normalize_spaces(item.get("pe_office"))
        contractor = cls._normalize_spaces(item.get("contractor_name") or item.get("winner"))
        status = cls._normalize_spaces(item.get("work_status") or item.get("completion_status") or item.get("status")).lower()
        start_date = cls._to_iso_date(item.get("contract_start_date"))
        end_date = cls._to_iso_date(item.get("contract_end_date") or item.get("planned_completion_date") or item.get("actual_completion_date"))
        amount = cls._safe_float(item.get("contract_value_bdt") or item.get("amount_bdt") or item.get("contract_value"))
        combined = " ".join(v.lower() for v in (title, pe_office, contractor) if v)
        if not title or not pe_office or cls._should_exclude_contractor_name(contractor):
            return False
        if any(marker in combined for marker in ("home page", "forgot password", "user login", "annual procurement plans", "econtracts", "eexperience", "copyright", "view all notifications")):
            return False
        if status not in {"completed", "ongoing"}:
            return False
        if amount <= 0:
            return False
        if not start_date or not end_date:
            return False
        return True
    async def _load_agency_cache(self) -> List[Dict[str, str]]:
        from app.models.intelligence import Agency

        if self.__class__._agency_cache is None:
            result = await self.db.execute(select(Agency))
            self.__class__._agency_cache = [
                {
                    "agency_code": agency.agency_code or "",
                    "agency_name": agency.agency_name or "",
                    "keyword": agency.keyword or "",
                }
                for agency in result.scalars().all()
            ]
        return self.__class__._agency_cache
    @staticmethod
    def _normalize_spaces(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()
    @staticmethod
    def _numeric_tender_id(*values: Any) -> Optional[str]:
        for value in values:
            match = re.search(r"(?<!\d)(\d{5,12})(?!\d)", str(value or ""))
            if match:
                return match.group(1)
        return None
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
    def _safe_bool(value: Any) -> Optional[bool]:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        raw = str(value).strip().lower()
        if raw in {"true", "yes", "y", "1", "completed on time", "on time"}:
            return True
        if raw in {"false", "no", "n", "0", "delayed", "late"}:
            return False
        return None
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
    async def get_agency_comparison(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        from app.models.intelligence import EContractExecution as EE

        await self._ensure_eexperience_schema()
        conditions = [EE.agency_code.is_not(None)]
        if source:
            conditions.append(EE.data_source == source)
        where = and_(*conditions)

        result = await self.db.execute(
            select(
                EE.agency_code,
                func.count(EE.id).label("contract_count"),
                func.coalesce(func.sum(EE.contract_value_bdt), 0).label("total_value"),
                func.avg(func.coalesce(EE.progress_pct, 0)).label("avg_progress"),
                func.avg(func.coalesce(EE.delay_days, 0)).label("avg_delay"),
                func.count(func.distinct(EE.contractor_name)).label("unique_contractors"),
            )
            .where(where)
            .group_by(EE.agency_code)
            .order_by(func.count(EE.id).desc())
        )
        return [
            {
                "agency_code": r[0],
                "contract_count": int(r[1]),
                "total_value_bdt": round(float(r[2]), 2),
                "avg_progress_pct": round(float(r[3] or 0), 2),
                "avg_delay_days": round(float(r[4] or 0), 1),
                "unique_contractors": int(r[5]),
            }
            for r in result.all()
        ]
    async def get_agency_intelligence(self, agency_code: Optional[str] = None) -> List[Dict[str, Any]]:
        from app.models.intelligence import AgencyIntelligence

        stmt = select(AgencyIntelligence)
        if agency_code:
            stmt = stmt.where(AgencyIntelligence.agency_code == agency_code)
        stmt = stmt.order_by(AgencyIntelligence.total_amount_bdt.desc())
        result = await self.db.execute(stmt)
        return [self._row_to_dict(r) for r in result.scalars().all()]
    async def get_agent_feed(self, agency: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
        from app.models.intelligence import ContractorDNA
        lifecycle = await self.query_lifecycle(agency=agency, limit=limit, offset=0)
        contractors = await self.list_contractors(limit=min(limit, 20), offset=0)
        agency_intel = await self.get_agency_intelligence(agency)
        contractor_stats = await self.get_contractor_stats()
        lifecycle_stats = await self.get_lifecycle_stats()
        data_quality = await self.get_award_data_quality_stats()
        live_tender_stats = await self.get_live_tender_stats(agency=agency)
        eexperience_stats = await self.get_eexperience_stats()
        recent_eexperience = await self.query_eexperience(agency=agency, limit=min(limit, 10), offset=0)
        execution_intelligence = await self.get_execution_intelligence(agency=agency, limit=min(limit, 8))
        rate_quoted = await self.get_rate_quoted_analysis(agency=agency, limit=min(limit, 10))
        from app.models.intelligence import EContractExecution
        execution_total, matched_to_tender = (
            await self.db.execute(
                select(
                    func.count(EContractExecution.id),
                    func.count(EContractExecution.id).filter(EContractExecution.procurement_tender_id.is_not(None)),
                )
            )
        ).one()
        execution_total = int(execution_total or 0)
        matched_to_tender = int(matched_to_tender or 0)
        lifecycle_execution_match = {
            "tender_match_rate_pct": round((matched_to_tender / execution_total) * 100, 2) if execution_total else 0,
            "app_match_rate_pct": 0,
            "matched_to_tender": matched_to_tender,
            "matched_to_app": 0,
            "unmatched": execution_total - matched_to_tender,
        }
        # Top contractors by eExperience completion performance
        top_performers = sorted(
            (await self.db.execute(
                select(ContractorDNA).order_by(ContractorDNA.completion_rate.desc()).limit(10)
            )).scalars().all(),
            key=lambda x: x.completion_rate,
            reverse=True,
        )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agency_filter": agency,
            "lifecycle_stats": lifecycle_stats,
            "data_quality": data_quality,
            "contractor_stats": contractor_stats,
            "live_tender_stats": live_tender_stats,
            "eexperience_stats": eexperience_stats,
            "execution_intelligence": execution_intelligence,
            "rate_quoted": {
                "total_award_bdt": rate_quoted["total_award_bdt"],
                "total_completed_bdt": rate_quoted["total_completed_bdt"],
                "total_variance_bdt": rate_quoted["total_variance_bdt"],
                "avg_variance_pct": rate_quoted["avg_variance_pct"],
                "delayed_count": rate_quoted["delayed_count"],
                "sample_records": rate_quoted["records"],
                "by_agency": rate_quoted["by_agency"],
            },
            "lifecycle_execution_match": lifecycle_execution_match,
            "top_contractors_by_completion": [
                {
                    "contractor_id": c.contractor_id,
                    "completion_rate": c.completion_rate,
                    "on_time_rate": c.on_time_rate,
                    "avg_delay_days": c.avg_delay_days,
                    "total_experience_contracts": c.total_experience_contracts,
                }
                for c in top_performers
            ],
            "recent_lifecycle": lifecycle["records"],
            "recent_eexperience": recent_eexperience["records"],
            "top_contractors": contractors,
            "agency_intelligence": agency_intel[: min(limit, 20)],
        }
    async def get_award_data_quality_stats(self):
        return await self._app_noa.get_award_data_quality_stats()
    async def get_award_trends(self, agency_code: Optional[str] = None, period: str = "monthly") -> List[Dict[str, Any]]:
        from app.models.intelligence import ProcurementLifecycle as PL
        fiscal_q = func.left(PL.award_date, 4).label("fy")
        agency_q = PL.agency_code
        if agency_code:
            agency_q = func.coalesce(PL.agency_code, "UNKNOWN")
        stmt = select(
            fiscal_q,
            agency_q.label("agency_code"),
            func.count(PL.id).label("award_count"),
            func.coalesce(func.sum(PL.award_amount_bdt), 0).label("total_amount_bdt"),
            func.avg(PL.npp_ratio).label("avg_npp"),
        ).where(PL.award_amount_bdt > 0).group_by(fiscal_q, agency_q).order_by(fiscal_q.desc())
        if agency_code:
            stmt = stmt.where(PL.agency_code == agency_code)
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "fy": r[0] or "Unknown",
                "agency_code": r[1] or "UNKNOWN",
                "award_count": int(r[2] or 0),
                "total_amount_bdt": round(float(r[3] or 0), 2),
                "avg_npp": round(float(r[4] or 0), 4),
            }
            for r in rows
        ]
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
    async def get_department_tree(self) -> List[Dict[str, Any]]:
        from app.models.intelligence import Agency, APPRecord, ProcurementTender
        if self._department_tree_cache is not None:
            return self._department_tree_cache

        ministry_expr = func.coalesce(Agency.ministry, Agency.agency_name, ProcurementTender.agency_code, "Unknown Ministry")
        office_expr = func.coalesce(ProcurementTender.pe_office, Agency.agency_name, ProcurementTender.agency_code, "Unknown Office")
        result = await self.db.execute(
            select(
                ministry_expr.label("ministry"),
                office_expr.label("office"),
                func.count(ProcurementTender.id).label("package_count"),
                func.coalesce(func.sum(APPRecord.estimated_cost_bdt), 0).label("total_estimated_bdt"),
            )
            .outerjoin(APPRecord, APPRecord.procurement_tender_id == ProcurementTender.id)
            .outerjoin(Agency, Agency.agency_code == ProcurementTender.agency_code)
            .group_by(ministry_expr, office_expr)
            .order_by(ministry_expr.asc(), office_expr.asc())
        )
        ministries: Dict[str, Dict[str, Any]] = {}
        for ministry, office, package_count, total_estimated_bdt in result.all():
            ministry = ministry or "Unknown Ministry"
            office = office or "Unknown Office"
            ministry_entry = ministries.setdefault(
                ministry,
                {
                    "id": ministry,
                    "name": ministry,
                    "type": "Ministry",
                    "office_count": 0,
                    "total_packages": 0,
                    "offices": [],
                },
            )
            ministry_entry["offices"].append(
                {
                    "id": office,
                    "name": office,
                    "package_count": int(package_count or 0),
                    "total_estimated_bdt": round(float(total_estimated_bdt or 0), 2),
                }
            )
            ministry_entry["total_packages"] += int(package_count or 0)

        tree: List[Dict[str, Any]] = []
        for ministry in sorted(ministries.keys()):
            entry = ministries[ministry]
            entry["offices"] = sorted(entry["offices"], key=lambda item: item["name"])
            entry["office_count"] = len(entry["offices"])
            tree.append(entry)

        self._department_tree_cache = tree
        return tree
    async def get_eexperience_stats(self, source: Optional[str] = None) -> Dict[str, Any]:
        from app.models.intelligence import EContractExecution as EE

        await self._ensure_eexperience_schema()
        cond = [EE.data_source == source] if source else []
        where = and_(*cond) if cond else text("1=1")
        total, total_value, total_completed_value, agencies, contractors, completed_records, delayed_records = (
            await self.db.execute(
                select(
                    func.count(EE.id),
                    func.coalesce(func.sum(EE.contract_value_bdt), 0),
                    func.coalesce(func.sum(EE.completed_value_bdt), 0),
                    func.count(func.distinct(EE.agency_code)).filter(EE.agency_code.is_not(None)),
                    func.count(func.distinct(EE.contractor_name)).filter(EE.contractor_name.is_not(None)),
                    func.count(EE.id).filter(
                        or_(EE.actual_completion_date.is_not(None), EE.completion_status.ilike("%complete%"), EE.status.ilike("%complete%"))
                    ),
                    func.count(EE.id).filter(
                        or_(EE.delay_days > 0, EE.completed_on_time.is_(False), EE.completion_status.ilike("%delay%"))
                    ),
                ).where(where)
            )
        ).one()
        return {
            "total_records": int(total or 0),
            "total_value_bdt": round(float(total_value or 0), 2),
            "total_completed_value_bdt": round(float(total_completed_value or 0), 2),
            "unique_agencies": int(agencies or 0),
            "unique_contractors": int(contractors or 0),
            "completed_records": int(completed_records or 0),
            "delayed_records": int(delayed_records or 0),
        }
    async def get_eexperience_timeline(
        self,
        source: Optional[str] = None,
        granularity: str = "month",
        year: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        from app.models.intelligence import EContractExecution as EE

        await self._ensure_eexperience_schema()
        conditions = []
        if source:
            conditions.append(EE.data_source == source)
        if year:
            conditions.append(EE.contract_start_date.startswith(str(year)))
        where = and_(*conditions) if conditions else text("1=1")

        if granularity == "year":
            date_part = func.left(EE.contract_start_date, 4)
        else:
            date_part = func.left(EE.contract_start_date, 7)

        result = await self.db.execute(
            select(
                date_part.label("period"),
                func.count(EE.id).label("count"),
                func.coalesce(func.sum(EE.contract_value_bdt), 0).label("total_value"),
                func.coalesce(func.sum(EE.completed_value_bdt), 0).label("completed_value"),
                func.avg(func.coalesce(EE.progress_pct, 0)).label("avg_progress"),
            )
            .where(and_(where, EE.contract_start_date.is_not(None)))
            .group_by(date_part)
            .order_by(date_part)
        )
        return [
            {
                "period": r[0],
                "contract_count": int(r[1]),
                "total_value_bdt": round(float(r[2]), 2),
                "completed_value_bdt": round(float(r[3]), 2),
                "avg_progress_pct": round(float(r[4] or 0), 2),
            }
            for r in result.all()
        ]
    async def get_execution_intelligence(self, agency: Optional[str] = None, source: Optional[str] = None, limit: int = 8) -> Dict[str, Any]:
        from app.models.intelligence import EContractExecution as EE

        await self._ensure_eexperience_schema()
        conditions = []
        if agency:
            conditions.append(or_(EE.agency_code.ilike(f"%{agency}%"), EE.agency_name.ilike(f"%{agency}%"), EE.pe_office.ilike(f"%{agency}%")))
        if source:
            conditions.append(EE.data_source == source)
        where_clause = and_(*conditions) if conditions else text("1=1")

        completion_rate_expr = func.avg(
            case(
                (or_(EE.actual_completion_date.is_not(None), EE.completion_status.ilike("%complete%"), EE.status.ilike("%complete%")), 1.0),
                else_=0.0,
            )
        )
        on_time_rate_expr = func.avg(
            case(
                (EE.completed_on_time.is_(True), 1.0),
                else_=0.0,
            )
        )
        avg_progress_expr = func.avg(func.coalesce(EE.progress_pct, 0))
        avg_delay_expr = func.avg(func.coalesce(EE.delay_days, 0))

        summary_row = (
            await self.db.execute(
                select(
                    func.count(EE.id),
                    func.coalesce(func.sum(EE.completed_value_bdt), 0),
                    completion_rate_expr,
                    on_time_rate_expr,
                    avg_progress_expr,
                    avg_delay_expr,
                ).where(where_clause)
            )
        ).one()

        status_rows = (
            await self.db.execute(
                select(
                    func.coalesce(EE.completion_status, EE.work_status, EE.status, "unknown").label("status_label"),
                    func.count(EE.id).label("count"),
                )
                .where(where_clause)
                .group_by("status_label")
                .order_by(func.count(EE.id).desc())
                .limit(6)
            )
        ).all()

        recent = await self.query_eexperience(agency=agency, source=source, limit=limit, offset=0)
        return {
            "summary": {
                "total_records": int(summary_row[0] or 0),
                "completed_value_bdt": round(float(summary_row[1] or 0), 2),
                "completion_rate_pct": round(float(summary_row[2] or 0) * 100, 2),
                "on_time_rate_pct": round(float(summary_row[3] or 0) * 100, 2),
                "avg_progress_pct": round(float(summary_row[4] or 0), 2),
                "avg_delay_days": round(float(summary_row[5] or 0), 2),
            },
            "status_breakdown": [
                {"status": row[0] or "unknown", "count": int(row[1] or 0)}
                for row in status_rows
            ],
            "recent_records": recent["records"],
        }
    async def get_executive_overview(self) -> Dict[str, Any]:
        # Return cached result if fresh
        cached = _overview_cache.get("exec_overview")
        if cached and (_time.time() - cached.get("_ts", 0)) < _OVERVIEW_CACHE_TTL:
            return cached

        from app.models.intelligence import APPRecord, AwardRecordV2, Contractor, ProcurementLifecycle, ProcurementTender
        from app.agents import AgentRegistry
        from app.agents.orchestrator import PIPELINE_DEFINITION, PipelinePhase

        total_tenders = await self.db.scalar(select(func.count(ProcurementTender.id)))
        total_app = await self.db.scalar(select(func.count(APPRecord.id)))
        total_awards = await self.db.scalar(select(func.count(AwardRecordV2.id)))
        total_contractors = await self.db.scalar(select(func.count(Contractor.id)))
        knowledge_total = await self.db.scalar(
            text("SELECT COUNT(*) FROM knowledge_entries WHERE COALESCE(is_archived, false) = false")
        )
        knowledge_domains = (
            await self.db.execute(text("""
                SELECT entry_type, COUNT(*) AS total
                FROM knowledge_entries
                WHERE COALESCE(is_archived, false) = false
                GROUP BY entry_type
                ORDER BY total DESC
            """))
        ).mappings().all()
        matched = await self.db.scalar(
            select(func.count(ProcurementLifecycle.id)).where(ProcurementLifecycle.match_type == "package_exact")
        )
        total_lifecycle = await self.db.scalar(select(func.count(ProcurementLifecycle.id)))
        # eExperience / eCMS stats
        from app.models.intelligence import EContractExecution as EE
        ee_total = await self.db.scalar(select(func.count(EE.id)).where(EE.data_source == "EEXPERIENCE_ALL"))
        ecms_total = await self.db.scalar(select(func.count(EE.id)).where(EE.data_source == "ECMS_ONGOING"))
        ee_value = await self.db.scalar(select(func.coalesce(func.sum(EE.contract_value_bdt), 0)).where(EE.data_source == "EEXPERIENCE_ALL"))
        ecms_value = await self.db.scalar(select(func.coalesce(func.sum(EE.contract_value_bdt), 0)).where(EE.data_source == "ECMS_ONGOING"))

        registry = AgentRegistry()
        agent_list = registry.list_agents()
        agent_lookup = {agent["agent_id"]: agent for agent in agent_list}
        # Registry entries are initialized as ``pending`` until their first
        # orchestrated run. They are registered and callable, so excluding
        # that state made the dashboard report 0/51 company health despite a
        # complete registry.
        active_statuses = {"pending", "registered", "idle", "success", "ready", "running"}
        phase_rows: List[Dict[str, Any]] = []
        by_phase: Dict[str, int] = {}
        phase_labels: Dict[str, str] = {}
        phased_agent_ids: set[str] = set()

        for phase in PipelinePhase:
            agent_ids = PIPELINE_DEFINITION.get(phase, [])
            registered_agents = [agent_lookup[aid] for aid in agent_ids if aid in agent_lookup]
            registered_ids = [agent["agent_id"] for agent in registered_agents]
            phase_label = phase.value.replace("_", " ").title()
            phase_labels[phase.value] = phase_label
            by_phase[phase.value] = len(registered_agents)
            phased_agent_ids.update(registered_ids)
            phase_rows.append({
                "phase": phase.value,
                "label": phase_label,
                "total": len(agent_ids),
                "registered": len(registered_agents),
                "agents": agent_ids,
                "registered_agents": registered_ids,
            })

        total_pipeline_agents = len(phased_agent_ids)
        active_agents = sum(1 for agent in agent_list if agent.get("status") in active_statuses)
        result = {
            "slt": {"total_evaluations": 0, "evaluations": []},
            "agents": {
                "total": len(agent_list),
                "active": active_agents,
                "by_phase": by_phase,
                "phase_labels": phase_labels,
                "agent_list": agent_list,
            },
            "bwdb": {
                "tenders_scanned": total_tenders or 0,
                "bwdb_matches": matched or 0,
                "alerts": [],
                "alert_count": 0,
            },
            "embedding": {
                "knowledge_total": knowledge_total or 0,
                "by_domain": {
                    row["entry_type"] or "unknown": row["total"]
                    for row in knowledge_domains
                },
            },
            "pipeline": {
                "phases": phase_rows,
                "total_agents_phased": total_pipeline_agents,
            },
            "predictions": {"total_predictions": total_lifecycle or 0, "contractors_with_data": total_contractors or 0},
            "cross_check": {"status": "available", "total_predictions": total_lifecycle or 0, "indexed_awards": total_awards or 0},
            "npp": {
                "total_npp_records": await self.db.scalar(
                    select(func.count(ProcurementLifecycle.id)).where(ProcurementLifecycle.npp_ratio > 0)
                ) or 0,
                "by_agency": {},
                "agencies_with_data": [],
            },
            "documents": {
                "reports_generated": 0,
                "services_available": ["tender_doc_generator", "template_filler", "boq_excel_generator"],
            },
            "storage": {
                "base_dir": str(RUNTIME_DIR),
                "knowledge_lake": knowledge_total or 0,
                "bwdb_records": matched or 0,
                "econtracts_records": total_awards or 0,
            },
            "execution": {
                "eexperience_completed": int(ee_total or 0),
                "ecms_ongoing": int(ecms_total or 0),
                "eexperience_value_bdt": round(float(ee_value or 0), 2),
                "ecms_value_bdt": round(float(ecms_value or 0), 2),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        result["_ts"] = _time.time()
        _overview_cache["exec_overview"] = result
        return result
    #: Display name -> physical table, for the row-count summary.
    _IMPORT_COUNT_TABLES = {
        "tenders": "procurement_tenders",
        "app_records": "app_records",
        "live_tender_sources": "live_tender_sources",
        "awards": "award_records_v2",
        "eexperience": "econtract_execution",
        "lifecycle": "procurement_lifecycle",
        "contractors": "contractors",
        "contractor_dna": "contractor_dna",
    }

    async def get_import_counts(self, exact: bool = False) -> Dict[str, int]:
        """Row counts for the import summary.

        Defaults to planner estimates from pg_class. PostgreSQL cannot answer
        COUNT(*) without walking the table, and these eight tables total ~5.5M
        rows, so the exact form costs a full scan each — around a minute per
        table under concurrent load, with no caching in front of it. The
        estimates come from a single index lookup and are accurate to within a
        percent or so of the last ANALYZE, which is well inside what a
        dashboard figure needs.

        Pass ``exact=True`` where the precise number matters. Do not use either
        form to test whether a table has any rows; call :meth:`has_any_rows`,
        which stops at the first one.
        """
        if exact:
            from app.models.intelligence import (
                APPRecord, AwardRecordV2, ContractorDNA, Contractor,
                EContractExecution, LiveTenderSource, ProcurementLifecycle,
                ProcurementTender,
            )
            models = {
                "tenders": ProcurementTender, "app_records": APPRecord,
                "live_tender_sources": LiveTenderSource, "awards": AwardRecordV2,
                "eexperience": EContractExecution, "lifecycle": ProcurementLifecycle,
                "contractors": Contractor, "contractor_dna": ContractorDNA,
            }
            return {
                name: int(await self.db.scalar(select(func.count(model.id))) or 0)
                for name, model in models.items()
            }

        rows = await self.db.execute(
            text("""
                SELECT relname, GREATEST(reltuples, 0)::bigint AS estimate
                FROM pg_class
                WHERE relname = ANY(:names) AND relkind IN ('r', 'p')
            """),
            {"names": list(self._IMPORT_COUNT_TABLES.values())},
        )
        by_table = {r.relname: int(r.estimate) for r in rows}
        return {
            name: by_table.get(table, 0)
            for name, table in self._IMPORT_COUNT_TABLES.items()
        }

    async def has_any_rows(self, *names: str) -> Dict[str, bool]:
        """Whether each named table holds at least one row.

        Uses EXISTS so the scan stops at the first row. Callers deciding
        "is this already populated" want this rather than a count, and an
        estimate is not safe for that test — reltuples is -1 on a table that
        has never been analysed.
        """
        out: Dict[str, bool] = {}
        for name in names:
            table = self._IMPORT_COUNT_TABLES.get(name, name)
            out[name] = bool(await self.db.scalar(
                text(f"SELECT EXISTS (SELECT 1 FROM {table})")
            ))
        return out
    async def get_lifecycle_stats(self) -> Dict[str, Any]:
        from app.models.intelligence import ProcurementLifecycle as PL

        total, total_estimated, total_awarded, matched_packages, matched_total, title_similarity = (
            await self.db.execute(
                select(
                    func.count(PL.id),
                    func.coalesce(func.sum(PL.estimated_cost_bdt), 0),
                    func.coalesce(func.sum(PL.award_amount_bdt), 0),
                    func.count(PL.id).filter(PL.match_type == "package_exact"),
                    func.count(PL.id).filter(PL.data_source == "matched"),
                    func.count(PL.id).filter(PL.match_type == "title_similarity"),
                )
            )
        ).one()
        total_records = int(total or 0)
        matched_total_count = int(matched_total or 0)
        return {
            "total_records": total_records,
            "total_estimated_bdt": round(float(total_estimated or 0), 2),
            "total_award_bdt": round(float(total_awarded or 0), 2),
            "matched_packages": int(matched_packages or 0),
            "matched_total": matched_total_count,
            "title_similarity_matches": int(title_similarity or 0),
            "match_rate_pct": round((matched_total_count / total_records) * 100, 2) if total_records else 0.0,
        }
    async def get_live_tender_stats(self, agency: Optional[str] = None) -> Dict[str, Any]:
        from app.models.intelligence import LiveTenderSource as LT, ProcurementTender as PT

        stmt = select(LT, PT).join(PT, PT.id == LT.procurement_tender_id)
        if agency:
            stmt = stmt.where(or_(PT.agency_code == agency, LT.procuring_entity.ilike(f"%{agency}%")))
        rows = (await self.db.execute(stmt)).all()
        deadlines = [self._to_iso_date(live.deadline) for live, _ in rows if self._to_iso_date(live.deadline)]
        return {
            "total_live_tenders": len(rows),
            "with_real_estimate": sum(1 for live, _ in rows if self._safe_float(live.estimated_value_bdt) > 0),
            "active_agencies": len({tender.agency_code for live, tender in rows if tender.agency_code}),
            "latest_deadline": max(deadlines) if deadlines else None,
        }
    async def get_rate_quoted_analysis(
        self,
        agency: Optional[str] = None,
        contractor: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        from app.models.intelligence import EContractExecution as EE

        await self._ensure_eexperience_schema()
        conditions = [EE.contract_value_bdt > 0, EE.completed_value_bdt > 0]
        if agency:
            conditions.append(or_(EE.agency_code.ilike(f"%{agency}%"), EE.agency_name.ilike(f"%{agency}%")))
        if contractor:
            conditions.append(EE.contractor_name.ilike(f"%{contractor}%"))
        if source:
            conditions.append(EE.data_source == source)
        where = and_(*conditions)

        records_q = await self.db.execute(
            select(
                EE.id, EE.package_no, EE.title, EE.agency_code, EE.agency_name,
                EE.contractor_name, EE.contract_value_bdt, EE.completed_value_bdt,
                EE.fiscal_year, EE.completion_status, EE.delay_days, EE.completed_on_time,
                EE.data_source,
            )
            .where(where)
            .order_by(EE.contract_value_bdt.desc())
            .offset(offset)
            .limit(limit)
        )
        records = []
        for r in records_q.all():
            award_val = float(r.contract_value_bdt or 0)
            completed_val = float(r.completed_value_bdt or 0)
            variance = round(completed_val - award_val, 2)
            variance_pct = round((variance / award_val) * 100, 2) if award_val else 0.0
            records.append({
                "id": str(r.id),
                "package_no": r.package_no,
                "title": r.title,
                "agency_code": r.agency_code,
                "agency_name": r.agency_name,
                "contractor_name": r.contractor_name,
                "award_value_bdt": award_val,
                "completed_value_bdt": completed_val,
                "variance_bdt": variance,
                "variance_pct": variance_pct,
                "fiscal_year": r.fiscal_year,
                "completion_status": r.completion_status,
                "delay_days": r.delay_days,
                "completed_on_time": r.completed_on_time,
                "data_source": r.data_source,
            })

        # Aggregations
        agg_q = await self.db.execute(
            select(
                func.count(EE.id),
                func.sum(EE.contract_value_bdt),
                func.sum(EE.completed_value_bdt),
                func.avg(
                    func.nullif(
                        (EE.completed_value_bdt - EE.contract_value_bdt) / func.nullif(EE.contract_value_bdt, 0),
                        0,
                    )
                ),
                func.count(func.nullif(EE.delay_days, 0)),
            ).where(where)
        )
        agg = agg_q.one()
        total_count = int(agg[0] or 0)
        total_award = float(agg[1] or 0)
        total_completed = float(agg[2] or 0)
        avg_variance_pct = round(float(agg[3] or 0) * 100, 2) if agg[3] else 0.0
        delayed_count = int(agg[4] or 0)

        # Per-agency breakdown
        agency_agg_q = await self.db.execute(
            select(
                EE.agency_code,
                func.count(EE.id),
                func.sum(EE.contract_value_bdt),
                func.sum(EE.completed_value_bdt),
            )
            .where(and_(where, EE.agency_code.is_not(None)))
            .group_by(EE.agency_code)
            .order_by(func.count(EE.id).desc())
        )
        by_agency = []
        for r in agency_agg_q.all():
            av = float(r[2] or 0)
            cv = float(r[3] or 0)
            by_agency.append({
                "agency_code": r[0],
                "record_count": int(r[1]),
                "total_award_bdt": round(av, 2),
                "total_completed_bdt": round(cv, 2),
                "variance_bdt": round(cv - av, 2),
                "variance_pct": round(((cv - av) / av) * 100, 2) if av else 0.0,
            })

        return {
            "records": records,
            "total_count": total_count,
            "total_award_bdt": round(total_award, 2),
            "total_completed_bdt": round(total_completed, 2),
            "total_variance_bdt": round(total_completed - total_award, 2),
            "avg_variance_pct": avg_variance_pct,
            "delayed_count": delayed_count,
            "by_agency": by_agency,
            "limit": limit,
            "offset": offset,
        }
    async def import_eexperience_from_json(self, json_path: Path, progress: Optional[ImportProgress] = None) -> int:
        from app.models.intelligence import EContractExecution

        if not json_path.exists():
            return 0
        await self._ensure_eexperience_schema()
        records = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(records, dict):
            records = records.get("records", records.get("experience", [records]))
        imported = 0
        processed = 0
        ops_since_commit = 0
        existing = {
            (r.tender_id, r.contractor_name or "", r.contract_start_date or "")
            for r in (await self.db.execute(select(EContractExecution))).scalars().all()
        }
        for item in records:
            if not self._is_valid_eexperience_record(item):
                continue
            tender_id = self._numeric_tender_id(item.get("tender_id"), item.get("source_tender_id"))
            source_ref = str(self._coalesce(item.get("source_tender_id"), item.get("id"), item.get("package_no"), "")).strip()
            contractor = (item.get("contractor_name") or item.get("winner") or "").strip()
            start_date = self._to_iso_date(item.get("contract_start_date"))
            dedup_key = (tender_id or source_ref, contractor, start_date or "")
            if dedup_key in existing:
                continue
            # Never use numeric source_ref/tender_id as package_no fallback
            _pkg = self._coalesce(
                item.get("package_no"),
                item.get("package_name"),
                item.get("contract_no"),
                item.get("ref_no"),
            )
            # Only use source_ref if it is not purely numeric (eGP tender ID)
            if not _pkg and source_ref and not re.match(r"^\d{6,}$", source_ref):
                _pkg = source_ref
            package_no = self.normalize_package_no(_pkg)
            if not package_no:
                continue
            agency_code = item.get("agency_code") or await self._guess_agency_code(
                str(item.get("agency_name") or item.get("pe_office") or "")
            )
            planned_completion_date = self._to_iso_date(
                self._coalesce(item.get("planned_completion_date"), item.get("scheduled_completion_date"), item.get("completion_due_date"))
            )
            actual_completion_date = self._to_iso_date(
                self._coalesce(item.get("actual_completion_date"), item.get("completed_date"), item.get("completion_date"), item.get("work_completion_date"))
            )
            completion_status = self._coalesce(
                item.get("completion_status"),
                item.get("completion_state"),
                item.get("completed_works_status"),
                item.get("status"),
            )
            progress_pct = self._safe_float(
                self._coalesce(item.get("progress_pct"), item.get("completion_pct"), item.get("completion_progress"), item.get("work_progress"))
            )
            delay_days = self._safe_int(
                self._coalesce(item.get("delay_days"), item.get("completion_delay_days"), item.get("delayed_days"))
            )
            extension_days = self._safe_int(
                self._coalesce(item.get("extension_days"), item.get("time_extension_days"), item.get("extended_days"))
            )
            completed_on_time = self._safe_bool(
                self._coalesce(item.get("completed_on_time"), item.get("on_time_completion"))
            )
            self.db.add(
                EContractExecution(
                    id=self._uuid(),
                    package_no=package_no,
                    title=self._coalesce(item.get("title"), item.get("name_of_work"), item.get("package_name")),
                    agency_code=agency_code,
                    agency_name=self._coalesce(item.get("agency_name"), item.get("organization_name"), item.get("ministry_division")),
                    pe_office=self._coalesce(item.get("pe_office"), item.get("pe_name"), item.get("organization_name")),
                    contractor_name=contractor or None,
                    contract_value_bdt=self._safe_float(
                        self._coalesce(item.get("contract_value_bdt"), item.get("amount_bdt"), item.get("contract_value"))
                    ),
                    completed_value_bdt=self._safe_float(
                        self._coalesce(item.get("completed_value_bdt"), item.get("executed_value_bdt"), item.get("final_bill_value_bdt"), item.get("completed_value"))
                    ),
                    contract_start_date=start_date,
                    contract_end_date=self._to_iso_date(item.get("contract_end_date")),
                    planned_completion_date=planned_completion_date,
                    actual_completion_date=actual_completion_date,
                    award_date=self._to_iso_date(item.get("award_date")),
                    status=item.get("status", "completed"),
                    completion_status=completion_status,
                    work_status=self._coalesce(item.get("work_status"), item.get("execution_status"), item.get("current_status")),
                    progress_pct=progress_pct,
                    delay_days=delay_days,
                    extension_days=extension_days,
                    completed_on_time=completed_on_time,
                    performance_rating=self._coalesce(item.get("performance_rating"), item.get("rating"), item.get("grade")),
                    completion_certificate_no=self._coalesce(item.get("completion_certificate_no"), item.get("completion_cert_no"), item.get("certificate_no")),
                    bill_no=self._coalesce(item.get("bill_no"), item.get("running_bill_no"), item.get("final_bill_no")),
                    fiscal_year=self._coalesce(item.get("fiscal_year"), item.get("financial_year")),
                    tender_id=tender_id or None,
                    district=item.get("district", ""),
                    source_url=item.get("source_url", ""),
                    data_source=item.get("source") or item.get("data_source") or "EEXPERIENCE",
                    remarks=self._coalesce(item.get("remarks"), item.get("notes"), item.get("comment")),
                    raw_payload=item,
                )
            )
            existing.add(dedup_key)
            imported += 1
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
    async def import_experience_to_dedicated_tables(self) -> Dict[str, int]:
        """Read all_completed.json + all_ongoing.json into dedicated tables."""
        from app.models.intelligence import EExperienceCompleted, ECMSongoing

        base = RUNTIME_DIR / "knowledge" / "eexperience_all"
        results = {"completed": 0, "ongoing": 0, "completed_skipped": 0, "ongoing_skipped": 0}

        # Existing keys for dedup
        existing_completed = {
            (r.package_no, r.contractor_name or "")
            for r in (await self.db.execute(select(EExperienceCompleted))).scalars().all()
        }
        existing_ongoing = {
            (r.package_no, r.contractor_name or "")
            for r in (await self.db.execute(select(ECMSongoing))).scalars().all()
        }

        for subdir, source, model_cls, existing_set, result_key in [
            ("completed", "EEXPERIENCE_ALL", EExperienceCompleted, existing_completed, "completed"),
            ("ongoing", "ECMS_ONGOING", ECMSongoing, existing_ongoing, "ongoing"),
        ]:
            fp = base / subdir / f"all_{subdir}.json"
            if not fp.exists():
                continue
            records = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(records, dict):
                records = records.get("records", records.get(subdir, []))
            imported = 0
            skipped = 0
            for item in records:
                if not isinstance(item, dict):
                    continue
                tender_id = self._numeric_tender_id(item.get("tender_id"), item.get("tender_proposal_id"))
                pno = self.normalize_package_no(
                    self._coalesce(
                        item.get("package_no"),
                        item.get("contract_no"),
                        item.get("package_name"),
                        item.get("ref_no"),
                    )
                )
                if not pno:
                    skipped += 1
                    continue
                cname = (item.get("contractor_name") or item.get("winner") or "").strip()
                dedup_key = (pno, cname)
                if dedup_key in existing_set:
                    skipped += 1
                    continue
                existing_set.add(dedup_key)
                start_date = self._to_iso_date(item.get("contract_start_date"))
                end_date = self._to_iso_date(item.get("contract_end_date"))
                planned = self._to_iso_date(item.get("planned_completion_date"))
                actual = self._to_iso_date(item.get("actual_completion_date"))
                pub_date = self._to_iso_date(item.get("published_date"))
                awd_date = self._to_iso_date(item.get("award_date"))

                self.db.add(model_cls(
                    id=self._uuid(),
                    tender_id=tender_id,
                    tender_ref_no=self._coalesce(item.get("tender_ref_no"), item.get("ref_no")),
                    package_no=pno,
                    package_name=self._coalesce(item.get("package_name"), item.get("title")),
                    name_of_work=self._coalesce(item.get("name_of_work"), item.get("work_name"), item.get("title")),
                    title=self._coalesce(item.get("title"), item.get("package_name"), item.get("name_of_work")),
                    ministry_division=self._coalesce(item.get("ministry_division"), item.get("ministry")),
                    organization_name=item.get("organization_name"),
                    pe_office=self._coalesce(item.get("pe_office"), item.get("pe_office_name"), item.get("procuring_entity")),
                    pe_name=item.get("pe_name"),
                    agency_code=item.get("agency_code") or await self._guess_agency_code(str(self._coalesce(item.get("organization_name"), item.get("pe_office"), item.get("title"), ""))) or "",
                    procurement_nature=item.get("procurement_nature"),
                    work_category=item.get("work_category"),
                    procurement_method=item.get("procurement_method", ""),
                    contractor_name=cname or None,
                    company_unique_id=item.get("company_unique_id", ""),
                    experience_certificate_no=self._coalesce(
                        item.get("experience_certificate_no"), item.get("completion_certificate_no")
                    ),
                    contract_no=self._coalesce(item.get("contract_no"), item.get("package_no")),
                    contract_value_bdt=self._safe_float(item.get("contract_value_bdt")),
                    completed_value_bdt=self._safe_float(item.get("completed_value_bdt")),
                    contract_start_date=start_date,
                    contract_end_date=end_date,
                    planned_completion_date=planned,
                    actual_completion_date=actual,
                    published_date=pub_date,
                    award_date=awd_date,
                    completion_status=self._coalesce(item.get("completion_status"), item.get("completion_state"), item.get("status")),
                    work_status=self._coalesce(item.get("work_status"), item.get("execution_status")),
                    status=item.get("status", ""),
                    progress_pct=self._safe_float(self._coalesce(item.get("progress_pct"), item.get("physical_progress_pct"))),
                    physical_progress_pct=self._safe_float(self._coalesce(item.get("physical_progress_pct"), item.get("progress_pct"))),
                    financial_progress_pct=self._safe_float(item.get("financial_progress_pct")),
                    physical_progress_date=self._to_iso_date(item.get("physical_progress_date")),
                    financial_progress_date=self._to_iso_date(item.get("financial_progress_date")),
                    completed_on_time=self._safe_bool(item.get("completed_on_time")),
                    is_jvca=self._safe_bool(item.get("is_jvca")),
                    remarks=item.get("remarks"),
                    comments_by_pe=item.get("comments_by_pe"),
                    district=item.get("district", ""),
                    source_url=item.get("source_url", ""),
                    procurement_tender_id=None,
                    data_source=source,
                    raw_payload=item,
                ))
                imported += 1
            results[result_key] = imported
            results[f"{result_key}_skipped"] = skipped

        # Batch apply agency_code updates
        for rkey, batch in updates.items():
            if batch:
                table = batch[0]["table"]
                await self.db.execute(
                    text(
                        f"UPDATE {table} "
                        "SET agency_code = :agency "
                        "WHERE tender_id = :tid "
                        "AND (agency_code IS NULL OR agency_code = '')"
                    ),
                    batch,
                )
        await self.db.flush()
        return results
    async def import_per_agency_experience(self) -> Dict[str, Any]:
        """Import per-agency experience.json files into dedicated tables.
        
        These files have agency_code populated (unlike the flat bulk crawl files).
        Upserts by tender_id: fills in empty agency_code for matching records,
        inserts new records for unmatched ones.
        """
        from app.models.intelligence import EExperienceCompleted, ECMSongoing

        base = RUNTIME_DIR / "knowledge" / "eexperience"
        all_exp_json = base / "all_experience.json"

        # Collect existing tender_ids for quick lookup
        existing_completed_ids = set()
        r = await self.db.execute(select(EExperienceCompleted.tender_id))
        for row in r:
            tid = row[0]
            if tid:
                existing_completed_ids.add(tid)

        existing_ongoing_ids = set()
        r = await self.db.execute(select(ECMSongoing.tender_id))
        for row in r:
            tid = row[0]
            if tid:
                existing_ongoing_ids.add(tid)

        # Determine whether to use all_experience.json (already aggregated)
        # or per-agency files. all_experience.json is a 1245-record subset
        # of the per-agency files (all its IDs exist in per-agency files).
        # We'll use per-agency files for completeness.
        results = {
            "completed_updated": 0,
            "completed_inserted": 0,
            "ongoing_updated": 0,
            "ongoing_inserted": 0,
            "errors": 0,
            "total_per_agency_records": 0,
        }

        agency_dirs = sorted([
            d for d in base.iterdir()
            if d.is_dir() and (d / "experience.json").exists()
        ])

        for agency_dir in agency_dirs:
            fp = agency_dir / "experience.json"
            try:
                records = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                results["errors"] += 1
                continue
            if not isinstance(records, list):
                continue

            agency_code_from_dir = agency_dir.name
            for item in records:
                if not isinstance(item, dict):
                    continue
                results["total_per_agency_records"] += 1
                status = item.get("status", "").lower()
                tender_id = self._numeric_tender_id(item.get("tender_id"), item.get("tender_proposal_id"))
                source_ref = str(self._coalesce(item.get("source_tender_id"), item.get("id"), item.get("package_no"), "")).strip()
                # Never use numeric tender_id or source_ref as package_no
                _pkg = self._coalesce(
                    item.get("package_no"),
                    item.get("package_name"),
                    item.get("contract_no"),
                    item.get("ref_no"),
                )
                if not _pkg and source_ref and not re.match(r"^\d{6,}$", source_ref):
                    _pkg = source_ref
                pno = self.normalize_package_no(_pkg)
                if not pno:
                    continue
                cname = (item.get("contractor_name") or item.get("winner") or "").strip()
                agency_code = item.get("agency_code") or agency_code_from_dir or ""

                if status == "ongoing":
                    model_cls = ECMSongoing
                    existing_ids = existing_ongoing_ids
                    source = "ECMS_PER_AGENCY"
                    rkey_updated = "ongoing_updated"
                    rkey_inserted = "ongoing_inserted"
                else:
                    model_cls = EExperienceCompleted
                    existing_ids = existing_completed_ids
                    source = "EEXPERIENCE_PER_AGENCY"
                    rkey_updated = "completed_updated"
                    rkey_inserted = "completed_inserted"

                if tender_id and tender_id in existing_ids:
                    # Update agency_code if empty
                    updates.setdefault(rkey_updated, []).append({"agency": agency_code, "tid": tender_id, "table": model_cls.__tablename__})
                    if model_cls == EExperienceCompleted:
                        existing_completed_ids.add(tender_id)
                    else:
                        existing_ongoing_ids.add(tender_id)
                    results[rkey_updated] += 1
                else:
                    # Insert new record
                    start_date = self._to_iso_date(item.get("contract_start_date"))
                    end_date = self._to_iso_date(item.get("contract_end_date"))
                    planned = self._to_iso_date(item.get("planned_completion_date"))
                    actual = self._to_iso_date(item.get("actual_completion_date"))
                    pub_date = self._to_iso_date(item.get("published_date"))
                    awd_date = self._to_iso_date(item.get("award_date"))

                    rec = model_cls(
                        id=self._uuid(),
                        tender_id=tender_id,
                        tender_ref_no=self._coalesce(item.get("tender_ref_no"), item.get("ref_no")),
                        package_no=pno,
                        package_name=self._coalesce(item.get("package_name"), item.get("title")),
                        name_of_work=self._coalesce(item.get("name_of_work"), item.get("work_name"), item.get("title")),
                        title=self._coalesce(item.get("title"), item.get("package_name"), item.get("name_of_work")),
                        ministry_division=self._coalesce(item.get("ministry_division"), item.get("ministry")),
                        organization_name=item.get("organization_name"),
                        pe_office=self._coalesce(item.get("pe_office"), item.get("pe_office_name"), item.get("procuring_entity")),
                        pe_name=item.get("pe_name"),
                        agency_code=agency_code,
                        procurement_nature=item.get("procurement_nature"),
                        work_category=item.get("work_category"),
                        procurement_method=item.get("procurement_method", ""),
                        contractor_name=cname or None,
                        company_unique_id=item.get("company_unique_id", ""),
                        experience_certificate_no=self._coalesce(
                            item.get("experience_certificate_no"), item.get("completion_certificate_no")
                        ),
                        contract_no=self._coalesce(item.get("contract_no"), item.get("package_no")),
                        contract_value_bdt=self._safe_float(item.get("contract_value_bdt")),
                        completed_value_bdt=self._safe_float(item.get("completed_value_bdt")),
                        contract_start_date=start_date,
                        contract_end_date=end_date,
                        planned_completion_date=planned,
                        actual_completion_date=actual,
                        published_date=pub_date,
                        award_date=awd_date,
                        completion_status=self._coalesce(
                            item.get("completion_status"), item.get("completion_state"), item.get("status")
                        ),
                        work_status=self._coalesce(item.get("work_status"), item.get("execution_status")),
                        status=item.get("status", ""),
                        progress_pct=self._safe_float(self._coalesce(item.get("progress_pct"), item.get("physical_progress_pct"))),
                        physical_progress_pct=self._safe_float(self._coalesce(item.get("physical_progress_pct"), item.get("progress_pct"))),
                        financial_progress_pct=self._safe_float(item.get("financial_progress_pct")),
                        physical_progress_date=self._to_iso_date(item.get("physical_progress_date")),
                        financial_progress_date=self._to_iso_date(item.get("financial_progress_date")),
                        completed_on_time=self._safe_bool(item.get("completed_on_time")),
                        is_jvca=self._safe_bool(item.get("is_jvca")),
                        remarks=item.get("remarks"),
                        comments_by_pe=item.get("comments_by_pe"),
                        district=item.get("district", ""),
                        source_url=item.get("source_url", ""),
                        data_source=source,
                        raw_payload=item,
                    )
                    self.db.add(rec)
                    existing_ids.add(tender_id)
                    results[rkey_inserted] += 1

        # Batch apply agency_code updates
        for rkey, batch in updates.items():
            if batch:
                table = batch[0]["table"]
                await self.db.execute(
                    text(
                        f"UPDATE {table} "
                        "SET agency_code = :agency "
                        "WHERE tender_id = :tid "
                        "AND (agency_code IS NULL OR agency_code = '')"
                    ),
                    batch,
                )
        await self.db.flush()
        return results
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
    async def list_eexperience_agencies(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        from app.models.intelligence import EContractExecution as EE

        await self._ensure_eexperience_schema()
        conds = [EE.agency_code.is_not(None)]
        if source:
            conds.append(EE.data_source == source)
        where = and_(*conds)
        result = await self.db.execute(
            select(EE.agency_code, func.count(EE.id).label("count"), func.sum(EE.contract_value_bdt).label("total_value"))
            .where(where)
            .group_by(EE.agency_code)
            .order_by(func.count(EE.id).desc())
        )
        return [
            {"agency_code": row[0], "record_count": int(row[1]), "total_value_bdt": round(float(row[2] or 0), 2)}
            for row in result.all()
        ]
    async def query_completed_executions(
        self,
        agency: Optional[str] = None,
        contractor: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        from app.models.intelligence import EExperienceCompleted as M

        where = self._build_execution_where(M, agency, contractor, date_from, date_to)
        total = await self.db.scalar(select(func.count(M.id)).where(where))
        rows = (
            await self.db.execute(
                select(M).where(where).order_by(M.contract_value_bdt.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return {
            "total": int(total or 0),
            "records": [self._row_to_dict(r) for r in rows],
            "limit": limit,
            "offset": offset,
        }
    async def query_eexperience(
        self,
        agency: Optional[str] = None,
        contractor: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        work_status: Optional[str] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        from app.models.intelligence import EContractExecution as EE

        await self._ensure_eexperience_schema()
        conditions = []
        if agency:
            conditions.append(or_(EE.agency_code.ilike(f"%{agency}%"), EE.agency_name.ilike(f"%{agency}%"), EE.pe_office.ilike(f"%{agency}%")))
        if contractor:
            conditions.append(EE.contractor_name.ilike(f"%{contractor}%"))
        if date_from:
            conditions.append(EE.contract_start_date >= date_from)
        if date_to:
            conditions.append(EE.contract_end_date <= date_to)
        if status:
            conditions.append(EE.status == status)
        if source:
            conditions.append(EE.data_source == source)
        if work_status:
            conditions.append(EE.work_status.ilike(f"%{work_status}%"))
        if min_value is not None:
            conditions.append(EE.contract_value_bdt >= min_value)
        if max_value is not None:
            conditions.append(EE.contract_value_bdt <= max_value)

        where_clause = and_(*conditions) if conditions else text("1=1")
        total = await self.db.scalar(select(func.count(EE.id)).where(where_clause))
        result = await self.db.execute(
            select(EE)
            .where(where_clause)
            .order_by(EE.actual_completion_date.desc().nullslast(), EE.contract_end_date.desc().nullslast(), EE.contract_start_date.desc().nullslast(), EE.package_no.asc())
            .limit(limit)
            .offset(offset)
        )
        return {
            "total": total or 0,
            "limit": limit,
            "offset": offset,
            "source_filter": source,
            "records": [self._row_to_dict(r) for r in result.scalars().all()],
        }
    async def query_lifecycle(
        self,
        agency: Optional[str] = None,
        zone: Optional[str] = None,
        contractor: Optional[str] = None,
        min_amount: float = 0,
        max_amount: float = 0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        method: Optional[str] = None,
        match_type: Optional[str] = None,
        data_source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        from app.models.intelligence import ProcurementLifecycle as PL
        from app.services.runtime_guards import cache_get, cache_set

        cache_key = (
            "ids_query_lifecycle:"
            f"{agency}:{zone}:{contractor}:{min_amount}:{max_amount}:"
            f"{date_from}:{date_to}:{method}:{match_type}:{data_source}:{limit}:{offset}"
        )
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        conditions = []
        if agency:
            conditions.append(PL.agency_code.ilike(f"%{agency}%"))
        if zone:
            conditions.append(PL.zone_name.ilike(f"%{zone}%"))
        if contractor:
            conditions.append(PL.winner.ilike(f"%{contractor}%"))
        if min_amount > 0:
            conditions.append(PL.award_amount_bdt >= min_amount)
        if max_amount > 0:
            conditions.append(PL.award_amount_bdt <= max_amount)
        if date_from:
            conditions.append(PL.award_date >= date_from)
        if date_to:
            conditions.append(PL.award_date <= date_to)
        if method:
            conditions.append(PL.procurement_method.ilike(f"%{method}%"))
        if match_type:
            conditions.append(PL.match_type == match_type)
        if data_source:
            conditions.append(PL.data_source == data_source)

        where_clause = and_(*conditions) if conditions else text("1=1")
        total = await self.db.scalar(select(func.count(PL.id)).where(where_clause))
        result = await self.db.execute(
            select(PL)
            .where(where_clause)
            .order_by(PL.award_date.desc().nullslast(), PL.package_no.asc())
            .limit(limit)
            .offset(offset)
        )
        payload = {
            "total": total or 0,
            "limit": limit,
            "offset": offset,
            "records": [self._row_to_dict(r) for r in result.scalars().all()],
        }
        await cache_set(cache_key, payload, ttl=120)
        return payload
    async def query_ongoing_executions(
        self,
        agency: Optional[str] = None,
        contractor: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        from app.models.intelligence import ECMSongoing as M

        where = self._build_execution_where(M, agency, contractor, date_from, date_to)
        total = await self.db.scalar(select(func.count(M.id)).where(where))
        rows = (
            await self.db.execute(
                select(M).where(where).order_by(M.contract_value_bdt.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return {
            "total": int(total or 0),
            "records": [self._row_to_dict(r) for r in rows],
            "limit": limit,
            "offset": offset,
        }
    async def rebuild_aggregate_intelligence(self) -> Dict[str, int]:
        from app.models.intelligence import (
            AgencyIntelligence,
            AwardIntelligence,
            DiscountPattern,
            ProcurementLifecycle,
            ZoneIntelligence,
        )

        await self.db.execute(delete(AgencyIntelligence))
        await self.db.execute(delete(ZoneIntelligence))
        await self.db.execute(delete(DiscountPattern))
        await self.db.execute(delete(AwardIntelligence))
        await self.db.flush()

        rows = (await self.db.execute(select(ProcurementLifecycle))).scalars().all()
        by_agency: Dict[str, list] = defaultdict(list)
        by_zone: Dict[str, list] = defaultdict(list)
        by_agency_quarter: Dict[tuple, list] = defaultdict(list)
        by_discount_bucket: Dict[tuple, list] = defaultdict(list)

        for row in rows:
            if row.agency_code:
                by_agency[row.agency_code].append(row)
            if row.zone_name:
                by_zone[row.zone_name].append(row)
            if row.agency_code:
                award_iso = self._to_iso_date(row.award_date) or "0000-01-01"
                year = award_iso[:4]
                quarter = 1
                if len(award_iso) >= 7 and award_iso[5:7].isdigit():
                    month = int(award_iso[5:7])
                    quarter = ((month - 1) // 3) + 1
                by_agency_quarter[(row.agency_code, year, quarter)].append(row)
                by_discount_bucket[(row.agency_code, row.zone_name or "", row.procurement_method or "")].append(row)

        for agency_code, agency_rows in by_agency.items():
            awards = [r for r in agency_rows if self._safe_float(r.award_amount_bdt) > 0]
            npps = [self._safe_float(r.npp_ratio) for r in awards if self._is_credible_npp_row(r)]
            self.db.add(
                AgencyIntelligence(
                    id=self._uuid(),
                    agency_code=agency_code,
                    total_contracts=len(awards),
                    total_amount_bdt=sum(self._safe_float(r.award_amount_bdt) for r in awards),
                    avg_npp=(sum(npps) / len(npps)) if npps else 0.0,
                    npp_trend="stable",
                    preferred_method=max(
                        (r.procurement_method for r in awards if r.procurement_method),
                        key=lambda method: sum(1 for r in awards if r.procurement_method == method),
                        default=None,
                    ),
                )
            )

        for zone_name, zone_rows in by_zone.items():
            awards = [r for r in zone_rows if self._safe_float(r.award_amount_bdt) > 0]
            npps = [self._safe_float(r.npp_ratio) for r in awards if self._is_credible_npp_row(r)]
            self.db.add(
                ZoneIntelligence(
                    id=self._uuid(),
                    zone_name=zone_name,
                    total_contracts=len(awards),
                    total_amount_bdt=sum(self._safe_float(r.award_amount_bdt) for r in awards),
                    active_agencies=len({r.agency_code for r in awards if r.agency_code}),
                    avg_npp=(sum(npps) / len(npps)) if npps else 0.0,
                )
            )

        for (agency_code, zone_name, method), bucket_rows in by_discount_bucket.items():
            npps = [self._safe_float(r.npp_ratio) for r in bucket_rows if self._is_credible_npp_row(r)]
            if not npps:
                continue
            ordered = sorted(npps)
            mid = len(ordered) // 2
            median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
            mean = sum(ordered) / len(ordered)
            stddev = (sum((v - mean) ** 2 for v in ordered) / len(ordered)) ** 0.5 if len(ordered) > 1 else 0.0
            self.db.add(
                DiscountPattern(
                    id=self._uuid(),
                    agency_code=agency_code,
                    zone_name=zone_name or None,
                    procurement_method=method or None,
                    sample_size=len(ordered),
                    avg_npp=mean,
                    min_npp=min(ordered),
                    max_npp=max(ordered),
                    median_npp=median,
                    stddev_npp=stddev,
                    total_amount_bdt=sum(self._safe_float(r.award_amount_bdt) for r in bucket_rows),
                )
            )

        for (agency_code, year, quarter), q_rows in by_agency_quarter.items():
            awards = [r for r in q_rows if self._safe_float(r.award_amount_bdt) > 0]
            if not awards:
                continue
            npps = [self._safe_float(r.npp_ratio) for r in awards if self._is_credible_npp_row(r)]
            self.db.add(
                AwardIntelligence(
                    id=self._uuid(),
                    agency_code=agency_code,
                    fiscal_year=year,
                    quarter=quarter,
                    total_contracts=len(awards),
                    total_amount_bdt=sum(self._safe_float(r.award_amount_bdt) for r in awards),
                    avg_npp=(sum(npps) / len(npps)) if npps else 0.0,
                    avg_contract_amount=sum(self._safe_float(r.award_amount_bdt) for r in awards) / len(awards),
                )
            )

        await self.db.flush()
        return {
            "agencies": len(by_agency),
            "zones": len(by_zone),
            "award_quarters": len(by_agency_quarter),
        }
