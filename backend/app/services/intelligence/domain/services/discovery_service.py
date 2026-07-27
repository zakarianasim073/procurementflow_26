"""DiscoveryService â€“ domain service extracted from IntelligenceDataService monolith."""
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
PACKAGE_PATTERNS = [
    re.compile(
        r"^\s*([a-z0-9][a-z0-9_.-]*(?:/[a-z0-9_.-]+)+)\s*(?:[|,:]\s*|\s{2,})(?=[a-z])",
        re.IGNORECASE,
    ),
    re.compile(r"\bpackage(?:\s+no\.?|\s*[:-])?\s*([a-z0-9][a-z0-9\-_/]+)\b", re.IGNORECASE),
    re.compile(r"\bpkg(?:\s+no\.?|\s*[:-])?\s*([a-z0-9][a-z0-9\-_/]+)\b", re.IGNORECASE),
    re.compile(r"\bwp[-/\s]*([0-9]{1,3}[a-z]?)\b", re.IGNORECASE),
    re.compile(r"\blot(?:\s+no\.?|\s*[:-])?\s*([a-z0-9][a-z0-9\-_/]+)\b", re.IGNORECASE),
    re.compile(r"\b([a-z]{1,8}-\d{1,4}[a-z]?)\b", re.IGNORECASE),
    re.compile(r"\b([a-z]{1,8}/\d{1,4}[a-z]?)\b", re.IGNORECASE),
]
MIN_CREDIBLE_NPP = 0.05
MAX_CREDIBLE_NPP = 1.5
MIN_CREDIBLE_ESTIMATE_BDT = 1000.0
MIN_CREDIBLE_AWARD_BDT = 1000.0
WORKS_RECORD_SCHEMA_VERSION = "2026-06-28"
DIVISION_KEYWORDS = {
    "DHAKA": "Dhaka",
    "MYMENSINGH": "Mymensingh",
    "CHATTOGRAM": "Chattogram",
    "CHITTAGONG": "Chattogram",
    "SYLHET": "Sylhet",
    "KHULNA": "Khulna",
    "BARISHAL": "Barishal",
    "RAJSHAHI": "Rajshahi",
    "RANGPUR": "Rangpur",
}
DISTRICT_TO_DIVISION = {
    "BAGERHAT": "Khulna",
    "BANDARBAN": "Chattogram",
    "BARGUNA": "Barishal",
    "BARISHAL": "Barishal",
    "BHOLA": "Barishal",
    "BOGRA": "Rajshahi",
    "BOGURA": "Rajshahi",
    "BRAHMANBARIA": "Chattogram",
    "CHANDPUR": "Chattogram",
    "CHATTOGRAM": "Chattogram",
    "CHITTAGONG": "Chattogram",
    "CHUADANGA": "Khulna",
    "COMILLA": "Chattogram",
    "CUMILLA": "Chattogram",
    "COX'S BAZAR": "Chattogram",
    "COXS BAZAR": "Chattogram",
    "DHAKA": "Dhaka",
    "DINAJPUR": "Rangpur",
    "FARIDPUR": "Dhaka",
    "FENI": "Chattogram",
    "GAIBANDHA": "Rangpur",
    "GAZIPUR": "Dhaka",
    "GOPALGANJ": "Dhaka",
    "HABIGANJ": "Sylhet",
    "JAMALPUR": "Mymensingh",
    "JASHORE": "Khulna",
    "JESSORE": "Khulna",
    "JHALOKATI": "Barishal",
    "JHENAIDAH": "Khulna",
    "JOYPURHAT": "Rajshahi",
    "KHAGRACHARI": "Chattogram",
    "KHULNA": "Khulna",
    "KISHOREGANJ": "Dhaka",
    "KURIGRAM": "Rangpur",
    "KUSHTIA": "Khulna",
    "LAKSHMIPUR": "Chattogram",
    "LALMONIRHAT": "Rangpur",
    "MADARIPUR": "Dhaka",
    "MAGURA": "Khulna",
    "MANIKGANJ": "Dhaka",
    "MEHERPUR": "Khulna",
    "MOULVIBAZAR": "Sylhet",
    "MUNSHIGANJ": "Dhaka",
    "MYMENSINGH": "Mymensingh",
    "NAOGAON": "Rajshahi",
    "NARAIL": "Khulna",
    "NARAYANGANJ": "Dhaka",
    "NARSINGDI": "Dhaka",
    "NATORE": "Rajshahi",
    "CHAPAINAWABGANJ": "Rajshahi",
    "NAWABGANJ": "Rajshahi",
    "NETROKONA": "Mymensingh",
    "NILPHAMARI": "Rangpur",
    "NOAKHALI": "Chattogram",
    "PABNA": "Rajshahi",
    "PANCHAGARH": "Rangpur",
    "PATUAKHALI": "Barishal",
    "PIROJPUR": "Barishal",
    "RAJBARI": "Dhaka",
    "RAJSHAHI": "Rajshahi",
    "RANGAMATI": "Chattogram",
    "RANGPUR": "Rangpur",
    "SATKHIRA": "Khulna",
    "SHARIATPUR": "Dhaka",
    "SHERPUR": "Mymensingh",
    "SIRAJGANJ": "Rajshahi",
    "SUNAMGANJ": "Sylhet",
    "SYLHET": "Sylhet",
    "TANGAIL": "Dhaka",
    "THAKURGAON": "Rangpur",
}
RUNTIME_DIR = Path(__file__).resolve().parent.parent.parent / "runtime"
LEGACY_ROOTS = [
    RUNTIME_DIR / "data_intel",
    RUNTIME_DIR / "knowledge",
    Path(__file__).resolve().parent.parent.parent.parent / "data",
]

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


class DiscoveryService(IntelligenceBaseService):
    """Domain service for discovery operations."""
    _agency_cache: Optional[List[Dict[str, str]]] = None

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.db = db
        self._batch_size = max(int(os.getenv("INTEL_IMPORT_BATCH_SIZE", "500")), 50)
        from app.services.app_noa_service import APPNOAMatchingService
        from app.services.experience_reconciliation_service import ExperienceReconciliationService

        self._app_noa = APPNOAMatchingService(db)
        self._experience = ExperienceReconciliationService(db)

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
    def _derive_discount_pct(cls, estimate: float, award: float, npp_ratio: float) -> float:
        if npp_ratio > 0:
            return round((1 - npp_ratio) * 100, 4)
        if estimate > 0 and award > 0:
            return round(((estimate - award) / estimate) * 100, 4)
        return 0.0
    @staticmethod
    def _derive_record_status(
        cls,
        *,
        live_status: Any = None,
        winner: Any = None,
        award_amount: float = 0.0,
        opening_report: Any = None,
    ) -> str:
        status = str(live_status or "").strip()
        if status:
            return status
        if winner or award_amount > 0:
            return "Awarded"
        if opening_report is not None:
            return "Opened"
        return "Unknown"
    async def _ensure_app_record_cache(self) -> Dict[str, Any]:
        from app.models.intelligence import APPRecord

        if self._app_record_cache is None:
            self._app_record_cache = {
                row.procurement_tender_id: row
                for row in (await self.db.execute(select(APPRecord))).scalars().all()
            }
        return self._app_record_cache
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
    async def _ensure_lifecycle_key_cache(self) -> set[tuple[str, str, Optional[str]]]:
        from app.models.intelligence import ProcurementLifecycle

        if self._lifecycle_key_cache is None:
            self._lifecycle_key_cache = {
                (row.package_no, row.winner or "", row.award_date)
                for row in (await self.db.execute(select(ProcurementLifecycle))).scalars().all()
            }
        return self._lifecycle_key_cache
    async def _ensure_live_tender_cache(self) -> Dict[str, Any]:
        from app.models.intelligence import LiveTenderSource

        if self._live_tender_cache is None:
            self._live_tender_cache = {
                row.source_tender_id: row
                for row in (await self.db.execute(select(LiveTenderSource))).scalars().all()
            }
        return self._live_tender_cache
    async def _ensure_tender_cache(self) -> Dict[str, Any]:
        from app.models.intelligence import ProcurementTender

        if self._tender_cache is None:
            self._tender_cache = {
                row.package_no: row
                for row in (await self.db.execute(select(ProcurementTender))).scalars().all()
            }
        return self._tender_cache
    def _extract_district_division(cls, *values: Any) -> tuple[str, str]:
        haystack = " | ".join(str(value or "") for value in values).upper()
        district = ""
        division = ""

        for div_key, div_name in DIVISION_KEYWORDS.items():
            if div_key in haystack:
                division = div_name
                break

        for district_key, div_name in DISTRICT_TO_DIVISION.items():
            if district_key in haystack:
                district = district_key.title().replace("S ", "s ")
                if not division:
                    division = div_name
                break

        return district, division
    def _extract_package_candidates(cls, *values: Any) -> List[str]:
        candidates: List[str] = []
        for value in values:
            if not value:
                continue
            normalized = cls.normalize_package_no(value)
            if normalized:
                candidates.append(normalized)
            extracted = cls._extract_package_from_title(str(value))
            if extracted:
                candidates.append(extracted)
        deduped: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate and candidate not in seen:
                deduped.append(candidate)
                seen.add(candidate)
        return deduped
    def _extract_package_from_title(cls, title: str) -> Optional[str]:
        for pattern in PACKAGE_PATTERNS:
            match = pattern.search(title or "")
            if match:
                candidate = cls.normalize_package_no(match.group(1))
                if candidate:
                    return candidate
        return None
    async def _get_or_create_tender(
        self,
        package_no: str,
        *,
        title: Optional[str] = None,
        agency_code: Optional[str] = None,
        pe_office: Optional[str] = None,
        procurement_method: Optional[str] = None,
        match_type: str = "unmatched_app",
    ):
        from app.models.intelligence import ProcurementTender

        cache = await self._ensure_tender_cache()
        tender = cache.get(package_no)
        if tender is None:
            tender = ProcurementTender(
                id=self._uuid(),
                package_no=package_no,
                title=title,
                agency_code=agency_code,
                pe_office=pe_office,
                procurement_method=procurement_method,
                match_type=match_type,
            )
            self.db.add(tender)
            await self.db.flush()
            cache[package_no] = tender
            return tender, True

        if title and not tender.title:
            tender.title = title
        if agency_code and not tender.agency_code:
            tender.agency_code = agency_code
        if pe_office and not tender.pe_office:
            tender.pe_office = pe_office
        if procurement_method and not tender.procurement_method:
            tender.procurement_method = procurement_method
        if tender.match_type != "package_exact" and match_type == "package_exact":
            tender.match_type = "package_exact"
        return tender, False
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
    @staticmethod
    def _iter_json_files() -> Iterable[Path]:
        def classify(path: Path) -> Optional[str]:
            lowered = str(path).replace("\\", "/").lower()
            name = path.name.lower()
            if name == "structure.json":
                return "app"
            if name == "contractors.json":
                return "contractor"
            if "/contractordna/" in lowered and name.endswith(".json"):
                return "contractor"
            if name == "flat.json" and "/econtracts/" in lowered:
                return "lifecycle"
            if name == "all_matches.json" and "/matches/" in lowered:
                return "lifecycle"
            if "/awards_batch/" in lowered:
                return "award"
            if name.startswith("awards_") or name.startswith("noa_") or "experience" in name:
                return "award"
            if "/tenders/" in lowered:
                return "tender"
            if name.startswith("tenders_") or name.startswith("bwdb_") or name.startswith("live_"):
                return "tender"
            return None

        priority = {"app": 0, "tender": 1, "award": 2, "contractor": 3, "lifecycle": 4}
        candidates: List[tuple[int, str, Path]] = []
        seen: set[Path] = set()
        for root in LEGACY_ROOTS:
            if not root.exists():
                continue
            for path in root.rglob("*.json"):
                if path in seen:
                    continue
                kind = classify(path)
                if not kind:
                    continue
                seen.add(path)
                candidates.append((priority[kind], str(path).lower(), path))
        for _, _, path in sorted(candidates):
            yield path
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
    def _normalize_live_estimate(cls, value: Any) -> float:
        amount = cls._safe_float(value)
        # Many live tender dumps contain ordinal row numbers in this field.
        if amount <= 1000:
            return 0.0
        return amount
    def _normalize_responsive_bidders(cls, bidders: Any) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        if not isinstance(bidders, list):
            return normalized

        for index, bidder in enumerate(bidders, start=1):
            if not isinstance(bidder, dict):
                continue
            bidder_name = cls._coalesce(
                bidder.get("bidder_name"),
                bidder.get("name"),
                bidder.get("contractor_name"),
                bidder.get("winner"),
            )
            if not bidder_name:
                continue
            quoted_amount = cls._safe_float(
                cls._coalesce(
                    bidder.get("final_amount"),
                    bidder.get("quoted_amount"),
                    bidder.get("amount"),
                    bidder.get("bid_amount"),
                )
            )
            discount_pct = cls._safe_float(
                cls._coalesce(
                    bidder.get("discount_pct"),
                    bidder.get("discount"),
                    bidder.get("discount_percent"),
                )
            )
            rank = cls._safe_int(bidder.get("rank")) or index
            normalized.append(
                {
                    "name": str(bidder_name).strip(),
                    "quoted_amount_bdt": quoted_amount,
                    "discount_pct": discount_pct,
                    "rank": rank,
                    "status": str(
                        cls._coalesce(
                            bidder.get("status"),
                            bidder.get("financial_status"),
                            bidder.get("evaluation_status"),
                            "responsive",
                        )
                    ).strip(),
                }
            )

        normalized.sort(key=lambda item: (item.get("rank") or 9999, item.get("quoted_amount_bdt") or 0))
        return normalized
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
    def _relative_path(path: Path) -> str:
        for base in (RUNTIME_DIR, *LEGACY_ROOTS):
            try:
                return str(path.relative_to(base)).replace("\\", "/")
            except ValueError:
                continue
        return path.name
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
    async def backfill_live_tender_shell_records(self) -> Dict[str, int]:
        """Delegate to TenderMatchingService."""
        from app.services.tender_matching_service import TenderMatchingService
        service = TenderMatchingService(self.db)
        return await service.backfill_live_tender_shell_records()

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
    async def rebuild_contractor_intelligence(self) -> Dict[str, int]:
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

    async def ingest_app_plan_record(self, item: Dict[str, Any], source_type: str = "egp_app_scan") -> Dict[str, Any]:
        from app.models.intelligence import APPRecord

        category = str(item.get("procurement_type") or item.get("category") or "").strip()
        if category.lower() != "works":
            return {
                "status": "skipped",
                "reason": "non_works",
                "source": source_type,
            }
        app_reference = str(self._coalesce(item.get("app_code"), item.get("package_no"), item.get("id"), "")).strip()
        title = self._coalesce(item.get("description"), item.get("title"), "")
        package_candidates = self._extract_package_candidates(item.get("package_no"), app_reference)
        title_package = self._extract_package_from_title(str(title))
        if title_package:
            package_candidates.append(title_package)
        package_no = package_candidates[0] if package_candidates else ""
        if not package_no:
            return {
                "status": "skipped",
                "reason": "missing_package_no",
                "source": source_type,
                "app_reference": app_reference,
            }
        entity = self._coalesce(item.get("procuring_entity"), item.get("agency"), item.get("department"))
        agency_code = await self._guess_agency_code(str(entity or title or ""))
        tender, _ = await self._get_or_create_tender(
            package_no,
            title=title,
            agency_code=agency_code,
            pe_office=entity,
            procurement_method=item.get("procurement_method"),
            match_type="unmatched_app",
        )

        app_cache = await self._ensure_app_record_cache()
        estimate_value = self._safe_float(self._coalesce(item.get("estimated_amount"), item.get("estimated_cost_bdt")))
        app_record = app_cache.get(tender.id)
        if app_record is None:
            app_record = APPRecord(
                id=self._uuid(),
                procurement_tender_id=tender.id,
                source_tender_id=self.normalize_package_no(app_reference) or package_no,
                package_no=package_no,
                title=title,
                estimated_cost_bdt=estimate_value,
                status=item.get("status"),
                published_date=self._to_iso_date(item.get("published_date")),
                deadline=self._to_iso_date(item.get("deadline")),
                financial_year=item.get("financial_year"),
                app_code=item.get("app_code") or source_type.upper(),
                category=category,
            )
            self.db.add(app_record)
            app_cache[tender.id] = app_record
        else:
            app_record.title = self._coalesce(app_record.title, title)
            app_record.estimated_cost_bdt = app_record.estimated_cost_bdt or estimate_value
            app_record.status = self._coalesce(app_record.status, item.get("status"))
            app_record.published_date = self._coalesce(app_record.published_date, self._to_iso_date(item.get("published_date")))
            app_record.deadline = self._coalesce(app_record.deadline, self._to_iso_date(item.get("deadline")))
            app_record.financial_year = self._coalesce(app_record.financial_year, item.get("financial_year"))
            app_record.category = self._coalesce(app_record.category, category)

        await self.db.flush()
        return self.build_works_record(tender=tender, app_record=app_record, source=source_type)

    async def rebuild_procurement_lifecycle(self) -> Dict[str, int]:
        """Delegate to TenderMatchingService."""
        from app.services.tender_matching_service import TenderMatchingService
        service = TenderMatchingService(self.db)
        return await service.rebuild_procurement_lifecycle()

    async def reconcile_award_package_mapping_from_json(self, flat_path, progress=None):
        return await self._app_noa.reconcile_award_package_mapping_from_json(flat_path, progress)

    async def reconcile_awards_to_app_records(self, progress=None):
        return await self._app_noa.reconcile_awards_to_app_records(progress)

    async def reconcile_eexperience_to_tender(self):
        return await self._experience.reconcile_eexperience_to_tender()
