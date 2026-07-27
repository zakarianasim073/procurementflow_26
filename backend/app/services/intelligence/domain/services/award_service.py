"""AwardService â€“ domain service extracted from IntelligenceDataService monolith."""
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
    re.compile(r"\bpackage(?:\s+no\.?|\s*[:-])?\s*([a-z0-9][a-z0-9\-_/]+)\b", re.IGNORECASE),
    re.compile(r"\bpkg(?:\s+no\.?|\s*[:-])?\s*([a-z0-9][a-z0-9\-_/]+)\b", re.IGNORECASE),
    re.compile(r"\bwp[-/\s]*([0-9]{1,3}[a-z]?)\b", re.IGNORECASE),
    re.compile(r"\blot(?:\s+no\.?|\s*[:-])?\s*([a-z0-9][a-z0-9\-_/]+)\b", re.IGNORECASE),
    re.compile(r"\b([a-z]{1,8}-\d{1,4}[a-z]?)\b", re.IGNORECASE),
    re.compile(r"\b([a-z]{1,8}/\d{1,4}[a-z]?)\b", re.IGNORECASE),
]
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


class AwardService(IntelligenceBaseService):
    """Domain service for award operations."""
    _agency_cache: Optional[List[Dict[str, str]]] = None

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.db = db
        self._batch_size = max(int(os.getenv("INTEL_IMPORT_BATCH_SIZE", "500")), 50)
        from app.services.app_noa_service import APPNOAMatchingService

        self._app_noa = APPNOAMatchingService(db)

    @staticmethod
    def _coalesce(*values: Any) -> Any:
        for value in values:
            if value not in (None, "", [], {}):
                return value
        return None
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
    async def _ensure_award_key_cache(self) -> set[tuple[str, str, Optional[str]]]:
        from app.models.intelligence import AwardRecordV2

        await self._ensure_award_schema()
        if self._award_key_cache is None:
            self._award_key_cache = {
                (row.procurement_tender_id, row.contractor_name or "", row.award_date)
                for row in (await self.db.execute(select(AwardRecordV2))).scalars().all()
            }
        return self._award_key_cache
    async def _ensure_award_schema(self) -> None:
        """Ensure award_records_v2 schema columns exist.

        .. deprecated::
            These ALTER TABLE statements should be moved to Alembic migration 006+.
            Runtime DDL causes schema drift invisible to `alembic revision --autogenerate`.
            This method is kept for backward compatibility on fresh deployments.
            Once the migration covers these columns, this method should become a no-op.
        """
        if self._award_schema_ready:
            return
        # Quick schema probe: skip if one representative column already exists
        probe = await self.db.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'award_records_v2' AND column_name = 'estimated_amount_bdt'"
            )
        )
        if probe.scalar_one_or_none():
            self._award_schema_ready = True
            return
        ddl = [
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS tender_id VARCHAR(100)",
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS estimated_amount_bdt DOUBLE PRECISION DEFAULT 0",
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS agency_confidence DOUBLE PRECISION DEFAULT 0",
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS procuring_entity VARCHAR(500)",
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS office VARCHAR(300)",
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS location VARCHAR(150)",
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'egp'",
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS raw_data JSON",
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS discount_pct DOUBLE PRECISION",
            "ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS npp_ratio DOUBLE PRECISION",
            "CREATE INDEX IF NOT EXISTS ix_arv2_tender_id ON award_records_v2 (tender_id)",
            "CREATE INDEX IF NOT EXISTS ix_arv2_agency_date ON award_records_v2 (agency_code, award_date)",
            "CREATE INDEX IF NOT EXISTS ix_arv2_tender_winner_date ON award_records_v2 (tender_id, contractor_name, award_date)",
        ]
        for stmt in ddl:
            await self.db.execute(text(stmt))
        await self.db.execute(text(
            "UPDATE award_records_v2 SET tender_id = NULL "
            "WHERE tender_id IS NOT NULL AND tender_id !~ '^[0-9]{5,12}$'"
        ))
        # NOTE: Do NOT blindly copy source_tender_id → tender_id.
        # source_tender_id should be the package number (per model docstring),
        # not the numeric e-GP ID. If tender_id is missing, leave it NULL
        # and let the reconciliation pipeline resolve it properly via
        # ProcurementTender lookup. The old code corrupted tender_id by
        # copying package numbers into it.
        # Proper resolution is done in reconcile_award_package_mapping.
        await self.db.execute(text(
            "UPDATE award_records_v2 SET procuring_entity = pe_office "
            "WHERE (procuring_entity IS NULL OR procuring_entity = '') AND pe_office IS NOT NULL"
        ))
        await self.db.execute(text(
            "UPDATE award_records_v2 SET office = pe_office "
            "WHERE (office IS NULL OR office = '') AND pe_office IS NOT NULL"
        ))
        await self.db.execute(text(
            "UPDATE award_records_v2 SET source = 'egp' WHERE source IS NULL OR source = ''"
        ))
        await self.db.commit()
        self._award_schema_ready = True
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

    async def reconcile_award_package_mapping_from_json(self, flat_path, progress=None):
        return await self._app_noa.reconcile_award_package_mapping_from_json(flat_path, progress)
    async def reconcile_awards_to_app_records(self, progress=None):
        return await self._app_noa.reconcile_awards_to_app_records(progress)


    async def list_awards_for_agent(self, agency="", limit=100):
        """List awards for an agent, delegated to APP-NOA matching service."""
        return await self._app_noa.list_awards_for_agent(agency, limit)

    async def get_award_data_quality_stats(self) -> Dict[str, Any]:
        """Deduplication stats on awards."""
        from app.models.intelligence import AwardRecordV2
        from sqlalchemy import select, func

        total = await self.db.execute(select(func.count(AwardRecordV2.id)))
        total_count = total.scalar()

        pkg = await self.db.execute(select(func.count(func.distinct(AwardRecordV2.package_no))))
        distinct_packages = pkg.scalar()

        return {
            "total_awards": total_count,
            "distinct_packages": distinct_packages,
            "duplicates": total_count - distinct_packages if total_count and distinct_packages else 0,
        }
