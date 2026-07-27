"""TenderService â€“ domain service extracted from IntelligenceDataService monolith."""
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


class TenderService(IntelligenceBaseService):
    """Domain service for tender operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.db = db
        self._batch_size = max(int(os.getenv("INTEL_IMPORT_BATCH_SIZE", "500")), 50)
        from app.services.experience_reconciliation_service import ExperienceReconciliationService

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
    def _compact_live_entity(cls, value: Any) -> str:
        parts = [cls._normalize_spaces(part) for part in str(value or "").split(",,")]
        parts = [part for part in parts if part]
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return " | ".join(parts)
        return " | ".join([parts[0], parts[-1]])
    def _derive_discount_pct(cls, estimate: float, award: float, npp_ratio: float) -> float:
        if npp_ratio > 0:
            return round((1 - npp_ratio) * 100, 4)
        if estimate > 0 and award > 0:
            return round(((estimate - award) / estimate) * 100, 4)
        return 0.0
    @staticmethod
    def _derive_record_status(
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
    def _extract_amount_unit_hint(cls, value: Any) -> Optional[str]:
        """Best-effort hint for whether a notice expressed money in Lakh or Crore."""
        if value in (None, "", [], {}):
            return None
        if isinstance(value, dict):
            preferred_keys = (
                "estimated_value", "estimated_amount", "estimated_cost", "amount", "cost",
                "budget", "value", "app_estimate", "estimate",
            )
            for key, item in value.items():
                key_text = str(key).lower()
                hint = cls._extract_amount_unit_hint(item)
                if hint:
                    return hint
                if any(token in key_text for token in preferred_keys):
                    hint = cls._extract_amount_unit_hint(item)
                    if hint:
                        return hint
            return None
        if isinstance(value, list):
            for item in value:
                hint = cls._extract_amount_unit_hint(item)
                if hint:
                    return hint
            return None

        text = cls._normalize_spaces(value)
        if not text:
            return None
        match = re.search(r"(?:tk|bdt|৳)?\s*[\d,]+(?:\.\d+)?\s*(crore|cr|lac|lakh)\b", text, re.IGNORECASE)
        if not match:
            return None
        unit = match.group(1).lower()
        if unit in {"crore", "cr"}:
            return "crore"
        if unit in {"lac", "lakh"}:
            return "lakh"
        return None
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
    @classmethod
    def _format_money_display(
        cls,
        amount: Any,
        unit_hint: Optional[str] = None,
        source_hint: Optional[str] = None,
    ) -> str:
        value = cls._safe_float(amount)
        if value <= 0:
            return "—"

        hint = (unit_hint or "").strip().lower()
        source = (source_hint or "").strip().upper()
        crore_value = value / 10_000_000
        lakh_value = value / 100_000
        if hint == "crore":
            return f"BDT {crore_value:,.2f} Cr"
        if hint == "lakh":
            return f"BDT {lakh_value:,.0f} Lakh" if abs(lakh_value - round(lakh_value)) < 0.01 else f"BDT {lakh_value:,.2f} Lakh"

        if source == "APP" and value < 100_000:
            return f"BDT {value:,.0f} Lakh" if abs(value - round(value)) < 0.01 else f"BDT {value:,.2f} Lakh"

        if source == "APP" and value < 100_000_000:
            return f"BDT {lakh_value:,.0f} Lakh" if abs(lakh_value - round(lakh_value)) < 0.01 else f"BDT {lakh_value:,.2f} Lakh"

        if value < 100_000:
            return f"BDT {value:,.2f}"

        if value < 10_000_000:
            return f"BDT {lakh_value:,.0f} Lakh" if abs(lakh_value - round(lakh_value)) < 0.01 else f"BDT {lakh_value:,.2f} Lakh"

        if abs(lakh_value - round(lakh_value)) < 0.01 and lakh_value < 100_000:
            return f"BDT {lakh_value:,.0f} Lakh"
        return f"BDT {crore_value:,.2f} Cr"
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
    def _infer_ministry_from_entity(cls, value: Any) -> str:
        parts = [cls._normalize_spaces(part) for part in str(value or "").split(",,")]
        parts = [part for part in parts if part]
        if parts:
            return parts[0]
        text = cls._normalize_spaces(value)
        return text or "Unknown Ministry"
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
    async def backfill_tender_regimes(self) -> Dict[str, int]:
        """
        Backfill regime labels on legacy tender rows.

        Existing records sometimes predate the `regime` column or have NULL/empty
        values after imports. This keeps the public dashboards and filters aligned
        with the PPR2008/PPR2025 split.

        .. note::
            The `ALTER TABLE tenders ADD COLUMN IF NOT EXISTS regime` block below
            should be moved to an Alembic migration (e.g., 006+) so that schema
            changes are tracked.  The column probe is a safety guard for deployments
            that pre-date the migration.
        """
        from app.agents.core.regime import get_regime

        columns_result = await self.db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'tenders'
                """
            )
        )
        columns = {row[0] for row in columns_result.all()}
        if "id" not in columns:
            return {"updated": 0, "total": 0, "skipped": 1}

        if "regime" not in columns:
            await self.db.execute(
                text(
                    """
                    ALTER TABLE tenders
                    ADD COLUMN IF NOT EXISTS regime VARCHAR(20) DEFAULT 'PPR2008'
                    """
                )
            )
            await self.db.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_tenders_regime
                    ON tenders (regime)
                    """
                )
            )
            columns.add("regime")

        date_column = next(
            (col for col in ("opening_date", "closing_date", "publication_date", "created_at") if col in columns),
            None,
        )
        if not date_column:
            return {"updated": 0, "total": 0, "skipped": 1}

        rows = (
            await self.db.execute(
                text(
                    # sql-ok: date_column from schema-inspected allowlist
                    f"""
                    SELECT id, {date_column} AS source_date, regime
                    FROM tenders
                    """
                )
            )
        ).all()
        updated = 0
        updates = []
        for row in rows:
            regime = get_regime(row.source_date)
            current_regime = row.regime
            if not current_regime or current_regime != regime:
                updates.append({"regime": regime, "id": row.id})
                updated += 1
        if updates:
            await self.db.execute(
                text("UPDATE tenders SET regime = :regime WHERE id = :id"),
                updates,
            )
            await self.db.flush()
        return {"updated": updated, "total": len(rows)}

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
    async def query_works_records(
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
        from app.models.procurement import OpeningReport
        from app.models.intelligence import APPRecord, AwardRecordV2, LiveTenderSource, ProcurementLifecycle, ProcurementTender

        base = await self.query_lifecycle(
            agency=agency,
            zone=zone,
            contractor=contractor,
            min_amount=min_amount,
            max_amount=max_amount,
            date_from=date_from,
            date_to=date_to,
            method=method,
            match_type=match_type,
            data_source=data_source,
            limit=limit,
            offset=offset,
        )
        if not base["records"]:
            return {"total": 0, "limit": limit, "offset": offset, "records": []}

        lifecycle_rows = (
            await self.db.execute(
                select(ProcurementLifecycle)
                .where(
                    ProcurementLifecycle.id.in_([record["id"] for record in base["records"] if record.get("id")])
                )
            )
        ).scalars().all()
        if not lifecycle_rows:
            return {"total": base["total"], "limit": limit, "offset": offset, "records": []}

        package_nos = {row.package_no for row in lifecycle_rows if row.package_no}
        tender_rows = (
            await self.db.execute(select(ProcurementTender).where(ProcurementTender.package_no.in_(package_nos)))
        ).scalars().all() if package_nos else []
        tender_by_package = {row.package_no: row for row in tender_rows}
        tender_ids = {row.id for row in tender_rows if row.id}
        tender_refs = {row.tender_id for row in lifecycle_rows if row.tender_id}

        app_rows = (
            await self.db.execute(select(APPRecord).where(APPRecord.procurement_tender_id.in_(tender_ids)))
        ).scalars().all() if tender_ids else []
        app_by_tender = {row.procurement_tender_id: row for row in app_rows}

        live_rows = (
            await self.db.execute(select(LiveTenderSource).where(LiveTenderSource.procurement_tender_id.in_(tender_ids)))
        ).scalars().all() if tender_ids else []
        live_by_tender: Dict[str, Any] = {}
        for row in live_rows:
            existing = live_by_tender.get(row.procurement_tender_id)
            if existing is None:
                live_by_tender[row.procurement_tender_id] = row
                continue
            existing_date = self._to_iso_date(existing.deadline)
            current_date = self._to_iso_date(row.deadline)
            if (current_date or "") > (existing_date or ""):
                live_by_tender[row.procurement_tender_id] = row

        award_rows = (
            await self.db.execute(select(AwardRecordV2).where(AwardRecordV2.procurement_tender_id.in_(tender_ids)))
        ).scalars().all() if tender_ids else []
        award_by_tender: Dict[str, Any] = {}
        for row in award_rows:
            existing = award_by_tender.get(row.procurement_tender_id)
            if existing is None:
                award_by_tender[row.procurement_tender_id] = row
                continue
            existing_date = self._to_iso_date(existing.award_date)
            current_date = self._to_iso_date(row.award_date)
            if (current_date or "") > (existing_date or ""):
                award_by_tender[row.procurement_tender_id] = row

        opening_rows = (
            await self.db.execute(select(OpeningReport).where(OpeningReport.tender_id.in_(tender_refs)))
        ).scalars().all() if tender_refs else []
        opening_by_tender = {row.tender_id: row for row in opening_rows}

        records: List[Dict[str, Any]] = []
        for lifecycle in lifecycle_rows:
            tender = tender_by_package.get(lifecycle.package_no)
            if tender is None:
                continue
            records.append(
                self.build_works_record(
                    lifecycle=lifecycle,
                    tender=tender,
                    app_record=app_by_tender.get(tender.id),
                    live_record=live_by_tender.get(tender.id),
                    award_record=award_by_tender.get(tender.id),
                    opening_report=opening_by_tender.get(lifecycle.tender_id),
                )
            )

        return {
            "total": base["total"],
            "limit": limit,
            "offset": offset,
            "records": records,
        }
    async def rebuild_procurement_lifecycle(self) -> Dict[str, int]:
        """Delegate to TenderMatchingService."""
        from app.services.tender_matching_service import TenderMatchingService
        service = TenderMatchingService(self.db)
        return await service.rebuild_procurement_lifecycle()
    async def reconcile_execution_to_lifecycle(self):
        return await self._experience.reconcile_execution_to_lifecycle()
    async def search_live_tenders(
        self,
        department_id: str = "",
        office_id: str = "",
        keyword: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        from app.models.intelligence import Agency, APPRecord, LiveTenderSource, ProcurementTender

        result = await self.db.execute(
            select(ProcurementTender, LiveTenderSource, APPRecord, Agency)
            .join(LiveTenderSource, LiveTenderSource.procurement_tender_id == ProcurementTender.id)
            .outerjoin(APPRecord, APPRecord.procurement_tender_id == ProcurementTender.id)
            .outerjoin(Agency, Agency.agency_code == ProcurementTender.agency_code)
            .order_by(LiveTenderSource.deadline.asc().nullslast(), ProcurementTender.package_no.asc())
        )
        keyword_lower = keyword.lower().strip()
        rows = []
        today = date.today().isoformat()
        excluded_status_terms = ("archived", "archive", "closed", "cancelled", "canceled", "awarded", "completed")
        live_status_terms = ("live", "open", "ongoing")

        for tender, live_record, app_record, agency in result.all():
            office_source = self._coalesce(live_record.procuring_entity, tender.pe_office, "")
            office = self._compact_live_entity(office_source)
            ministry = self._infer_ministry_from_entity(office_source)
            if (not ministry or ministry == "Unknown Ministry") and agency and agency.ministry:
                ministry = agency.ministry
            status = self._normalize_spaces(live_record.status or "").lower()
            deadline = self._to_iso_date(live_record.deadline)
            app_estimate = self._safe_float(getattr(app_record, "estimated_cost_bdt", 0) if app_record else 0)
            live_estimate = self._safe_float(live_record.estimated_value_bdt)
            has_app = bool(app_record and app_estimate > 0)
            app_unit_hint = self._extract_amount_unit_hint(
                self._coalesce(
                    getattr(app_record, "raw_payload", None),
                    live_record.raw_payload or {},
                )
            )
            primary_title = self._coalesce(
                app_record.title if app_record else None,
                live_record.title,
                tender.title,
                "",
            )
            primary_tender_id = self._coalesce(
                app_record.source_tender_id if app_record else None,
                live_record.source_tender_id,
                tender.package_no,
                "",
            )
            primary_package = self._coalesce(
                app_record.package_no if app_record and hasattr(app_record, "package_no") else None,
                tender.package_no,
                live_record.source_tender_id,
                primary_tender_id,
                "",
            )
            estimate = app_estimate if has_app else (live_estimate or app_estimate)

            if status and any(term in status for term in excluded_status_terms):
                continue
            if status and not any(term in status for term in live_status_terms):
                continue
            if deadline and deadline < today:
                continue
            if department_id and ministry.upper() != department_id.upper():
                continue
            if office_id and office.upper() != office_id.upper():
                continue
            if keyword_lower:
                haystack = " ".join(
                    [
                        tender.package_no or "",
                        live_record.title or tender.title or "",
                        office,
                        live_record.category or "",
                    ]
                ).lower()
                if keyword_lower not in haystack:
                    continue
            rows.append(
                {
                    "tender_id": primary_tender_id,
                    "package_no": tender.package_no,
                    "title": primary_title,
                    "app_tender_id": primary_tender_id,
                    "live_tender_id": primary_tender_id,
                    "app_work_name": primary_title,
                    "live_work_name": self._coalesce(live_record.title, tender.title, ""),
                    "app_estimated_value_bdt": round(app_estimate, 2),
                    "live_estimated_value_bdt": round(live_estimate, 2),
                    "procuring_entity": office,
                    "ministry": ministry,
                    "published_date": live_record.published_date or "",
                    "deadline": deadline or "",
                    "estimated_value_bdt": round(estimate, 2),
                    "estimated_value_source": "APP" if has_app else ("LIVE" if live_estimate else "NONE"),
                    "app_estimated_value_display": self._format_money_display(app_estimate, app_unit_hint, "APP") if has_app else "—",
                    "app_estimated_value_unit": app_unit_hint or "",
                    "notice_data": {
                        "tender_id": primary_tender_id,
                        "app_tender_id": primary_tender_id,
                        "live_tender_id": primary_tender_id,
                        "package_no": primary_package,
                        "work_name": primary_title,
                        "app_work_name": primary_title,
                        "live_work_name": self._coalesce(live_record.title, tender.title, ""),
                        "title": primary_title,
                        "estimated_cost_bdt": round(app_estimate if has_app else estimate, 2),
                        "estimated_amount_bdt": round(app_estimate if has_app else estimate, 2),
                        "app_estimated_value_bdt": round(app_estimate, 2),
                        "app_estimated_value_display": self._format_money_display(app_estimate, app_unit_hint, "APP") if has_app else "—",
                        "app_estimated_value_unit": app_unit_hint or "",
                        "live_estimated_value_bdt": round(live_estimate, 2),
                        "published_date": app_record.published_date if app_record else (live_record.published_date or ""),
                        "deadline": app_record.deadline if app_record else (deadline or ""),
                        "financial_year": app_record.financial_year if app_record else "",
                        "app_code": app_record.app_code if app_record else "",
                        "category": app_record.category if app_record else (live_record.category or ""),
                        "procuring_entity": office_source,
                        "ministry": ministry,
                        "live_status": live_record.status or "Live",
                        "live_value_bdt": round(live_estimate, 2),
                        "app_value_bdt": round(app_estimate, 2),
                        "raw_payload": live_record.raw_payload or {},
                    },
                    "category": live_record.category or "",
                    "location": "",
                    "status": live_record.status or "Live",
                }
            )

        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "tenders": rows[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }
