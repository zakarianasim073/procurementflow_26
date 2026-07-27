"""
Shared utilities for intelligence services.
Extracted from IntelligenceDataService to avoid duplication across focused services.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timezone, date
from difflib import SequenceMatcher
from html import unescape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PACKAGE_PATTERNS = [
    re.compile(r"\bpackage(?:\s+no\.?|\s*[:-])?\s*([a-z0-9][a-z0-9\-_/]+)\b", re.IGNORECASE),
    re.compile(r"\bpkg(?:\s+no\.?|\s*[:-])?\s*([a-z0-9][a-z0-9\-_/]+)\b", re.IGNORECASE),
    re.compile(r"\bwp[-/\s]*([0-9]{1,3}[a-z]?)\b", re.IGNORECASE),
    re.compile(r"\blot(?:\s+no\.?|\s*[:-])?\s*([a-z0-9][a-z0-9\-_/]+)\b", re.IGNORECASE),
    re.compile(r"\b([a-z]{1,8}-\d{1,4}[a-z]?)\b", re.IGNORECASE),
    re.compile(r"\b([a-z]{1,8}/\d{1,4}[a-z]?)\b", re.IGNORECASE),
]

LEADING_REFERENCE_PATTERN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9./_-]{4,80})\b")
TRAILING_DATETIME_PATTERN = re.compile(
    r"\s+\d{1,2}[-/][A-Za-z]{3,9}[-/]\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\s*$",
    re.IGNORECASE,
)

TITLE_STOPWORDS = {
    "construction", "reconstruction", "repair", "renovation", "improvement", "maintenance", "works", "work",
    "road", "bridge", "culvert", "under", "during", "year", "supply", "installation", "procurement",
    "office", "department", "division", "upazila", "district", "government", "building", "including",
    "necessary", "various", "different", "public", "worksdepartment", "fiscal", "period",
}

CONTRACTOR_EXCLUSION_PATTERNS = [
    re.compile(r"\bjv\b", re.IGNORECASE),
    re.compile(r"\bjoint venture\b", re.IGNORECASE),
    re.compile(r"\bconsortium\b", re.IGNORECASE),
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


class IntelligenceBaseService:
    """Base class providing shared utilities for all intelligence services."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.db = session  # Alias for domain services that use self.db
        self._caches: Dict[str, Any] = {}

    def _uuid(self) -> str:
        return str(uuid4())

    # ── Date / Type Helpers ───────────────────────────────────────────────

    def _to_iso_date(self, value) -> Optional[str]:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            value = value.strip()
            if value in ("", "None", "null", "N/A"):
                return None
            for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(value.split("T")[0] if "T" in value else value, "%Y-%m-%d" if fmt.startswith("%Y-%m-%d") and "T" not in value else fmt).date().isoformat()
                except ValueError:
                    continue
            return None
        return None

    def _safe_float(self, value) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            cleaned = str(value).replace(",", "").replace("BDT", "").replace("Tk.", "").replace("Tk", "").strip()
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return None

    def _safe_bool(self, value) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("true", "yes", "1", "active")
        return bool(value)

    # ── Normalization ─────────────────────────────────────────────────────

    @staticmethod
    def normalize_package_no(value: Any) -> str:
        from app.core.helpers import normalize_package_no

        return normalize_package_no(value)

    def _normalize_title(self, title: str) -> str:
        if not title:
            return ""
        t = unescape(title).strip().lower()
        t = re.sub(r"[^a-z0-9\s]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _normalize_contractor_name(self, name: str) -> str:
        if not name:
            return ""
        n = unescape(name).strip().upper()
        n = re.sub(r"[^A-Z0-9\s&.,]", " ", n)
        n = re.sub(r"\s+", " ", n).strip()
        return n

    def _normalize_contractor_alias(self, name: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", self._normalize_contractor_name(name))

    def _normalize_search_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"[^A-Z0-9]", "", unescape(text).strip().upper())

    # ── Matching ────────────────────────────────────────────────────────────

    def _contractor_match_score(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        a_norm = self._normalize_contractor_alias(a)
        b_norm = self._normalize_contractor_alias(b)
        if not a_norm or not b_norm:
            return 0.0
        if a_norm == b_norm:
            return 1.0
        return SequenceMatcher(None, a_norm, b_norm).ratio()

    def _is_credible_npp_row(self, row: Dict) -> bool:
        npp = self._safe_float(row.get("npp"))
        if npp is None:
            return False
        if not (MIN_CREDIBLE_NPP <= npp <= MAX_CREDIBLE_NPP):
            return False
        est = self._safe_float(row.get("estimated_cost"))
        if est is not None and est < MIN_CREDIBLE_ESTIMATE_BDT:
            return False
        award = self._safe_float(row.get("awarded_amount"))
        if award is not None and award < MIN_CREDIBLE_AWARD_BDT:
            return False
        return True

    def _should_exclude_contractor_name(self, name: str) -> bool:
        if not name:
            return True
        for pat in CONTRACTOR_EXCLUSION_PATTERNS:
            if pat.search(name):
                return True
        return False

    # ── Caching ────────────────────────────────────────────────────────────

    def _ensure_cache(self, name: str) -> Dict:
        if name not in self._caches:
            self._caches[name] = {}
        return self._caches[name]

    def _clear_caches(self):
        self._caches.clear()

    # ── JSON helpers ───────────────────────────────────────────────────────

    def _iter_json_files(self, root: Path, pattern: str = "*.json") -> Iterable[Path]:
        if root.exists():
            yield from root.rglob(pattern)

    def _relative_path(self, path: Path, roots: List[Path]) -> str:
        for r in roots:
            try:
                return str(path.relative_to(r))
            except ValueError:
                continue
        return str(path)

    def _coalesce(self, *values) -> Any:
        for v in values:
            if v is not None and v != "":
                return v
        return None

    def _numeric_tender_id(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return None

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {k: getattr(row, k) for k in row.__dict__ if not k.startswith("_")}

    # ── Agency / Division helpers ─────────────────────────────────────────

    def _extract_district_division(self, *values) -> tuple:
        try:
            from app.models.intelligence import DISTRICT_TO_DIVISION
        except ImportError:
            return None, None
        text = " ".join(str(v).upper() for v in values if v).strip()
        for district, division in DISTRICT_TO_DIVISION.items():
            if district in text:
                return district.title(), division
        return None, None

    def _guess_agency_code_from_keywords(self, text: str) -> Optional[str]:
        if not text:
            return None
        text_upper = text.upper()
        for keyword, agency in {
            "BWDB": "BWDB", "WATER DEVELOPMENT": "BWDB", "PWD": "PWD",
            "PUBLIC WORKS": "PWD", "LGED": "LGED", "LOCAL GOVERNMENT": "LGED",
            "RHD": "RHD", "ROAD HIGHWAY": "RHD", "RAILWAY": "BR",
        }.items():
            if keyword in text_upper:
                return agency
        return None

    def _guess_agency_code(self, record: Dict) -> Optional[str]:
        for field in ("agency", "procuring_entity", "department", "office", "ministry"):
            val = record.get(field)
            if val:
                agency = self._guess_agency_code_from_keywords(str(val))
                if agency:
                    return agency
        return None

    # ── Import helpers ────────────────────────────────────────────────────

    async def _commit_import_batch(self, items: List[Any]):
        if items:
            self.session.add_all(items)
            await self.session.flush()
            items.clear()

    # ── Path constants ──────────────────────────────────────────────────────

    @property
    def _runtime_dir(self) -> Path:
        return Path(os.getenv("BOQ_BASE_DIR", str(Path.home() / ".procurementflow-system")))

    @property
    def _legacy_roots(self) -> List[Path]:
        return [self._runtime_dir / "data"]

    # ── Works record builder (extracted from domain services to avoid duplication) ──

    def _derive_discount_pct(self, estimate: float, award: float, npp_ratio: float) -> float:
        if npp_ratio is not None and npp_ratio > 0:
            return round((1 - npp_ratio) * 100, 4)
        if estimate and estimate > 0 and award and award > 0:
            return round(((estimate - award) / estimate) * 100, 4)
        return 0.0

    def _derive_record_status(
        self,
        *,
        live_status: Any = None,
        winner: Any = None,
        award_amount: float = 0.0,
        opening_report: Any = None,
    ) -> str:
        status = str(live_status or "").strip()
        if status:
            return status
        if winner or (award_amount and award_amount > 0):
            return "Awarded"
        if opening_report is not None:
            return "Opened"
        return "Unknown"

    def _normalize_responsive_bidders(self, bidders: Any) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        if not isinstance(bidders, list):
            return normalized

        for index, bidder in enumerate(bidders, start=1):
            if not isinstance(bidder, dict):
                continue
            bidder_name = self._coalesce(
                bidder.get("bidder_name"),
                bidder.get("name"),
                bidder.get("contractor_name"),
                bidder.get("winner"),
            )
            if not bidder_name:
                continue
            quoted_amount = self._safe_float(
                self._coalesce(
                    bidder.get("final_amount"),
                    bidder.get("quoted_amount"),
                    bidder.get("amount"),
                    bidder.get("bid_amount"),
                )
            )
            discount_pct = self._safe_float(
                self._coalesce(
                    bidder.get("discount_pct"),
                    bidder.get("discount"),
                    bidder.get("discount_percent"),
                )
            )
            rank = self._safe_int(bidder.get("rank")) or index
            normalized.append(
                {
                    "name": str(bidder_name).strip(),
                    "quoted_amount_bdt": quoted_amount,
                    "discount_pct": discount_pct,
                    "rank": rank,
                    "status": str(
                        self._coalesce(
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

    def build_works_record(
        self,
        *,
        lifecycle=None,
        tender=None,
        app_record=None,
        live_record=None,
        award_record=None,
        opening_report=None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        tender_id = str(
            self._coalesce(
                self._numeric_tender_id(getattr(lifecycle, "tender_id", None)),
                self._numeric_tender_id(getattr(award_record, "tender_id", None)),
                self._numeric_tender_id(getattr(live_record, "source_tender_id", None)),
                self._numeric_tender_id(getattr(opening_report, "tender_id", None)),
                "",
            )
        ).strip()
        package_no = self.normalize_package_no(
            self._coalesce(
                getattr(lifecycle, "package_no", None),
                getattr(tender, "package_no", None),
                getattr(award_record, "package_no", None),
            )
        )
        title = self._coalesce(
            getattr(lifecycle, "title", None),
            getattr(award_record, "title", None),
            getattr(live_record, "title", None),
            getattr(tender, "title", None),
            "",
        )
        procuring_entity = self._coalesce(
            getattr(live_record, "procuring_entity", None),
            getattr(opening_report, "pe_office", None),
            getattr(award_record, "pe_office", None),
            getattr(tender, "pe_office", None),
            "",
        )
        pe_office = self._coalesce(
            getattr(opening_report, "pe_office", None),
            getattr(award_record, "pe_office", None),
            getattr(tender, "pe_office", None),
            getattr(live_record, "procuring_entity", None),
            "",
        )
        agency_target = self._coalesce(
            getattr(lifecycle, "agency_code", None),
            getattr(award_record, "agency_code", None),
            getattr(tender, "agency_code", None),
            getattr(opening_report, "agency", None),
            "",
        )
        district, division = self._extract_district_division(
            getattr(award_record, "district", None),
            getattr(opening_report, "zone", None),
            pe_office,
            procuring_entity,
            title,
        )
        estimated_cost_bdt = self._safe_float(
            self._coalesce(
                getattr(app_record, "estimated_cost_bdt", None),
                getattr(live_record, "estimated_value_bdt", None),
                getattr(opening_report, "estimated_amount_bdt", None),
                getattr(lifecycle, "estimated_cost_bdt", None),
            )
        )
        award_amount_bdt = self._safe_float(
            self._coalesce(
                getattr(lifecycle, "award_amount_bdt", None),
                getattr(award_record, "amount_bdt", None),
            )
        )
        npp_ratio = self._safe_float(getattr(lifecycle, "npp_ratio", None))
        responsive_bidders = self._normalize_responsive_bidders(getattr(opening_report, "bidders", None))
        bidder_count = len(responsive_bidders)
        winner = self._coalesce(
            getattr(lifecycle, "winner", None),
            getattr(award_record, "contractor_name", None),
            getattr(opening_report, "winner_name", None),
            "",
        )
        corrigenda = []
        if live_record is not None and isinstance(getattr(live_record, "raw_payload", None), dict):
            payload = live_record.raw_payload
            corrigenda = payload.get("corrigenda", []) or payload.get("corrigendum_urls", []) or []
        last_corrigendum_date = None
        if isinstance(corrigenda, list):
            dated = [str(item.get("date")) for item in corrigenda if isinstance(item, dict) and item.get("date")]
            if dated:
                last_corrigendum_date = max(dated)

        record_source = source or self._coalesce(
            getattr(live_record, "source_type", None),
            "opening_report" if opening_report is not None else None,
            "award_record" if award_record is not None else None,
            getattr(lifecycle, "data_source", None),
            "unknown",
        )
        record_status = self._derive_record_status(
            live_status=getattr(live_record, "status", None),
            winner=winner,
            award_amount=award_amount_bdt,
            opening_report=opening_report,
        )

        return {
            "schema_version": WORKS_RECORD_SCHEMA_VERSION,
            "tender_id": tender_id,
            "package_no": package_no,
            "title": title or "",
            "procuring_entity": str(procuring_entity or ""),
            "pe_office": str(pe_office or ""),
            "agency_target": str(agency_target or ""),
            "district": district,
            "division": division,
            "estimated_cost_bdt": estimated_cost_bdt,
            "award_amount_bdt": award_amount_bdt,
            "npp_ratio": npp_ratio,
            "discount_pct": self._derive_discount_pct(estimated_cost_bdt, award_amount_bdt, npp_ratio),
            "award_date": self._coalesce(
                getattr(lifecycle, "award_date", None),
                getattr(award_record, "award_date", None),
                None,
            ),
            "winner": str(winner or ""),
            "bidder_count": bidder_count,
            "responsive_bidders": responsive_bidders,
            "opening_report_available": opening_report is not None,
            "corrigenda_count": len(corrigenda) if isinstance(corrigenda, list) else 0,
            "last_corrigendum_date": last_corrigendum_date,
            "work_type": "Works",
            "procurement_method": str(
                self._coalesce(
                    getattr(lifecycle, "procurement_method", None),
                    getattr(award_record, "procurement_method", None),
                    getattr(tender, "procurement_method", None),
                    "",
                )
            ),
            "status": record_status,
            "source": str(record_source or "unknown"),
            "raw_data": {
                "lifecycle": self._row_to_dict(lifecycle) if lifecycle is not None else None,
                "tender": self._row_to_dict(tender) if tender is not None else None,
                "app_record": self._row_to_dict(app_record) if app_record is not None else None,
                "live_tender": self._row_to_dict(live_record) if live_record is not None else None,
                "award_record": self._row_to_dict(award_record) if award_record is not None else None,
                "opening_report": self._row_to_dict(opening_report) if opening_report is not None else None,
            },
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
