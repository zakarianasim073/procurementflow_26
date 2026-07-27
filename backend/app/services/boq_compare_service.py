"""BOQ comparison flows (T-013/API-01).

The full compare / brain-compare pipelines (APP estimate lookup, TDS criteria
extraction, SOR comparison, persistence) extracted from api/v1/boq.py so the
sync endpoints (BOQ_SYNC_FALLBACK deprecation window) and the Celery task
run the exact same code path — behavior is golden-verified (ADR-003/T-007).
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.intelligence import KnowledgeEntry
from app.models.boq import BOQComparison, BOQItem
from app.models.tender import Tender, TenderStatus
from app.models.user import User

logger = logging.getLogger(__name__)


class BOQCompareError(Exception):
    """Domain error with an HTTP-friendly status code (404 semantics preserved)."""

    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message)
        self.status_code = status_code


def resolve_zone(zone: Optional[str]) -> Tuple[Any, Optional[str]]:
    """zone can be a plain string (e.g. "B") or a JSON dict keyed by agency.

    Returns (resolved_zone for the processor, short string for the DB column).
    """
    zone_db_value = zone
    resolved_zone: Any = zone
    if zone and zone.startswith("{"):
        try:
            resolved_zone = json.loads(zone)
            zone_db_value = ",".join(f"{k}={v}" for k, v in sorted(resolved_zone.items()))
        except Exception:
            resolved_zone = zone
    return resolved_zone, zone_db_value


async def get_or_create_system_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == "system@procureflow.local"))
    system_user = result.scalar_one_or_none()
    if system_user:
        return system_user

    from app.core.security import hash_password

    system_user = User(
        id=str(uuid.uuid4()),
        email="system@procureflow.local",
        hashed_password=hash_password(settings.SYSTEM_USER_PASSWORD),
        full_name="System User",
        is_active=True,
        is_superuser=True,
    )
    db.add(system_user)
    await db.flush()
    return system_user


async def resolve_owner_user_id(db: AsyncSession, user: Optional[dict]) -> str:
    """Resolve a stable owner for guest/demo mode so saved comparisons remain visible."""
    user_id = user.get("id") if user and user.get("id") and user.get("id") != "guest" else None
    if user_id:
        existing_user = await db.get(User, user_id)
        if existing_user is None:
            user_id = None
    if not user_id:
        user_id = (await get_or_create_system_user(db)).id
    return user_id


def _to_optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_boq_item_row(tender_id: str, item: Dict[str, Any]) -> BOQItem:
    return BOQItem(
        id=str(uuid.uuid4()),
        tender_id=tender_id,
        item_no=str(item.get("item_no") or "")[:50] or None,
        code=str(item.get("code") or "")[:100] or None,
        description=str(item.get("description") or item.get("desc") or "")[:1000] or "BOQ item",
        unit=str(item.get("unit") or "")[:50] or None,
        quantity=_to_optional_float(item.get("qty") if "qty" in item else item.get("quantity")),
        quoted_rate=_to_optional_float(item.get("rate") if "rate" in item else item.get("quoted_rate")),
        sor_rate=_to_optional_float(item.get("sor_rate")),
        sor_code=str(item.get("sor_code") or item.get("sor_source") or "")[:100] or None,
        diff=_to_optional_float(item.get("diff")),
        pct_diff=_to_optional_float(item.get("pct_diff")),
        flag=str(item.get("flag") or "")[:50] or None,
        work_type=str(item.get("work_type") or "")[:100] or None,
        section=str(item.get("section") or "")[:100] or None,
        agency=str(item.get("agency") or "BWDB / PWD / LGED")[:20],
        attributes={
            "raw_item": item,
            "match_type": item.get("match_type"),
            "match_confidence": item.get("match_confidence"),
            "remarks": item.get("remarks"),
            "sor_desc": item.get("sor_desc"),
        },
    )


def extract_tds_criteria(tds_text: str) -> list[dict]:
    """Extract financial-criteria rows from e-GP TDS text (bracket format)."""

    def _rx(p):
        return re.search(p, tds_text, re.I | re.S)

    def _clean_val(v):
        """Extract numeric value from e-GP bracket format: [50,00,000] or [5500000] or 5500000"""
        v = v.strip().strip("[]()")
        v = v.replace(",", "")
        try:
            return int(v)
        except ValueError:
            return None

    criteria: Dict[str, str] = {}
    # General Experience — e-GP format: "shall be [5] years"
    m = _rx(r"general experience.*?shall be\s*\[?(\d+)\]?\s*years?")
    if m:
        criteria["General Experience"] = f"{m.group(1)} years"

    # Specific Experience — e-GP format: "value of at least Tk. [50,00,000]"
    m = _rx(r"value of at least Tk\.?\s*\[?([\d,]+)\]?")
    if m:
        val = _clean_val(m.group(1))
        if val:
            criteria["Specific Experience (min value)"] = f"Tk. {val:,}"

    # Avg Annual Turnover — e-GP format: "greater than Tk [55,00,000]"
    m = _rx(r"average annual construction turnover.*?greater than Tk\.?\s*\[?([\d,]+)\]?")
    if m:
        val = _clean_val(m.group(1))
        if val:
            criteria["Avg Annual Turnover"] = f"Tk. {val:,}"

    # Liquid Assets / Working Capital — e-GP format: "shall be Tk [17,50,000"
    m = _rx(r"(?:financial resources|liquid asset|working capital|credit line).*?shall be Tk\.?\s*\[?([\d,]+)")
    if m:
        val = _clean_val(m.group(1))
        if val:
            criteria["Liquid Assets / Credit Line"] = f"Tk. {val:,}"

    # Min Tender Capacity — e-GP format: "BDT [5500000]" or "minimum capacity shall be: BDT [5500000"
    m = _rx(r"(?:minimum tender capacity|minimum capacity shall be).*?(?:BDT|Tk)\.?\s*\[?([\d,]+)\]?")
    if m:
        val = _clean_val(m.group(1))
        if val:
            criteria["Min Tender Capacity"] = f"BDT {val:,}"

    # Tender Security — e-GP format: "The amount of the Tender Security shall be as per tender notice"
    m = _rx(r"Tender Security.*?(?:amount.*?(?:Tk\.?\s*\[?([\d,]+)\]?|as per tender notice))")
    if m:
        if m.group(1):
            val = _clean_val(m.group(1))
            if val:
                criteria["Tender Security"] = f"Tk. {val:,}"
        else:
            criteria["Tender Security"] = "As per tender notice"
    else:
        criteria["Tender Security"] = "As per tender notice"

    # Performance Security — e-GP format
    m = _rx(r"Performance Security shall(?:\s*not)?\s*be required")
    if m:
        criteria["Performance Security"] = "Not required"
    else:
        m = _rx(r"Performance Security.*?(?:rate of\s*(?:five|5)\s*\(?(\d+)\)?\s*percent)")
        if m:
            criteria["Performance Security"] = f"{m.group(1)}% of contract price"

    # Retention Money — e-GP format
    m = _rx(r"retention.*?(?:(\d+)\s*%|at the rate of\s*(?:five|5)\s*\(?(\d+)\)?\s*percent)")
    if m:
        pct = m.group(1) or m.group(2)
        if pct:
            criteria["Retention Money"] = f"{pct}% per certificate"

    return [
        {"criterion": k, "required": v, "our_figure": "", "remarks": "From TDS", "status": "PENDING"}
        for k, v in criteria.items()
    ]


async def _lookup_app_estimate(db: AsyncSession, package_no: str) -> Optional[float]:
    if not package_no:
        return None
    try:
        from app.models.intelligence import APPRecord as APPRec

        app_result = await db.execute(
            select(APPRec).where(APPRec.title.ilike(f"{package_no}%"))
            .order_by(APPRec.created_at.desc()).limit(1)
        )
        app_rec = app_result.scalar_one_or_none()
        if app_rec and app_rec.estimated_cost_bdt:
            return app_rec.estimated_cost_bdt
    except Exception:
        pass
    return None


async def _persist_comparison(
    db: AsyncSession,
    *,
    result: Dict[str, Any],
    tender_info_dict: Dict[str, Any],
    user_id: str,
    tender_public_id: str,
    tender_title: str,
    procuring_entity: str,
    zone_db_value: Optional[str],
    boq_file_id: str,
) -> BOQComparison:
    tender_result = await db.execute(select(Tender).where(Tender.tender_id == tender_public_id))
    tender = tender_result.scalar_one_or_none()
    if tender is None:
        tender = Tender(
            id=str(uuid.uuid4()),
            owner_id=user_id,
            tender_id=tender_public_id,
            title=tender_title[:500],
            procuring_entity=procuring_entity[:255],
            status=TenderStatus.ACTIVE,
            sor_agency="BWDB / PWD / LGED",
            zone=zone_db_value,
            extracted_data=tender_info_dict,
            comparison_results=result,
        )
        db.add(tender)
        await db.flush()
    else:
        tender.owner_id = user_id
        tender.title = tender_title[:500]
        tender.procuring_entity = procuring_entity[:255]
        tender.status = TenderStatus.ACTIVE
        tender.sor_agency = "BWDB / PWD / LGED"
        tender.zone = zone_db_value
        tender.extracted_data = tender_info_dict
        tender.comparison_results = result
        await db.flush()

    await db.execute(delete(BOQItem).where(BOQItem.tender_id == tender.id))
    for item in result.get("data", []) or []:
        db.add(build_boq_item_row(tender.id, item))

    comparison = BOQComparison(
        id=str(uuid.uuid4()),
        user_id=user_id,
        tender_id=tender.id,
        boq_file_id=boq_file_id,
        sor_agency="BWDB / PWD / LGED",
        zone=zone_db_value,
        total_items=result.get("total_items", 0),
        matches=result.get("matches", 0),
        variances=result.get("variances", 0),
        mismatches=result.get("mismatches", 0),
        below_sor=result.get("below_sor", 0),
        total_sor_amount=result.get("summary", {}).get("total_sor", 0.0),
        total_quoted_amount=result.get("summary", {}).get("total_quoted", 0.0),
        discount_pct=result.get("summary", {}).get("discount_pct", 0.0),
        summary_by_work_type=result.get("summary", {}).get("by_work_type", {}),
        excel_path=result.get("excel_path"),
        docx_path=result.get("docx_path"),
        tenderai_dir=result.get("tenderai_dir"),
        excel_object_key=result.get("excel_object_key"),
        docx_object_key=result.get("docx_object_key"),
    )
    db.add(comparison)
    await db.commit()
    return comparison


async def run_compare_flow(
    db: AsyncSession,
    *,
    boq_path: str,
    boq_file_id: str,
    sor_agency: str,
    zone: Optional[str],
    tender_info_dict: Dict[str, Any],
    user_id: str,
) -> Tuple[Dict[str, Any], str]:
    """Full /boq/compare pipeline. Returns (response payload, comparison id)."""
    resolved_zone, zone_db_value = resolve_zone(zone)
    upload_dir = Path(settings.BASE_DIR) / "uploads"
    boq_path_p = Path(boq_path)

    # ── Lookup APP Estimated Cost by package number ──
    package_no = tender_info_dict.get("package_no", "")
    if not package_no and "title" in tender_info_dict:
        pkg_match = re.search(r"([A-Za-z]+-\d+[A-Za-z]?/[\d-]+)", tender_info_dict["title"])
        if pkg_match:
            package_no = pkg_match.group(1)
    tender_info_dict["estimated_cost_app"] = await _lookup_app_estimate(db, package_no)

    # ── Extract TDS financial criteria if TDS PDF exists ──
    try:
        tender_id = tender_info_dict.get("tender_id", "")
        # Check both with and without /docs/ subdirectory
        tds_pdf = None
        for tds_dir_candidate in [
            upload_dir / str(tender_id) / "docs" / "Section2_Tender Data Sheet",
            upload_dir / str(tender_id) / "Section2_Tender Data Sheet",
        ]:
            if tds_dir_candidate.is_dir():
                for f in tds_dir_candidate.iterdir():
                    if f.suffix.lower() == ".pdf":
                        tds_pdf = f
                        break
            if tds_pdf:
                break

        if tds_pdf:
            import pdfplumber

            with pdfplumber.open(tds_pdf) as pdf:
                tds_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
            financial_check = extract_tds_criteria(tds_text)
            if financial_check:
                tender_info_dict["financial_check"] = financial_check
    except Exception:
        pass

    from app.services.boq_processor import BOQProcessor
    from app.sor.sor_service import sor_service

    processor = BOQProcessor()
    result = await processor.compare(
        boq_path=str(boq_path_p),
        sor_agency=sor_agency,
        zone=resolved_zone,
        sor_service=sor_service,
        tender_info=tender_info_dict,
    )

    result["comparison_id"] = boq_file_id
    result["sor_agency"] = "BWDB / PWD / LGED"
    result["zone"] = zone
    result["created_at"] = datetime.now(timezone.utc).isoformat()

    tender_public_id = str(
        tender_info_dict.get("tender_id")
        or tender_info_dict.get("package_no")
        or boq_file_id
    ).strip()
    tender_title = str(
        tender_info_dict.get("title")
        or tender_info_dict.get("entity")
        or boq_path_p.stem
    ).strip() or f"BOQ Analysis {boq_file_id}"
    procuring_entity = str(tender_info_dict.get("entity") or sor_agency).strip() or sor_agency

    comparison = await _persist_comparison(
        db,
        result=result,
        tender_info_dict=tender_info_dict,
        user_id=user_id,
        tender_public_id=tender_public_id,
        tender_title=tender_title,
        procuring_entity=procuring_entity,
        zone_db_value=zone_db_value,
        boq_file_id=boq_file_id,
    )

    response = {
        **result,
        "financial_check": tender_info_dict.get("financial_check", []),
        "estimated_cost_app": tender_info_dict.get("estimated_cost_app"),
    }
    return response, comparison.id


async def run_brain_compare_flow(
    db: AsyncSession,
    *,
    tender_id: str,
    sor_agency: str,
    zone: Optional[str],
    user_id: str,
) -> Tuple[Dict[str, Any], str]:
    """Full /boq/brain-compare pipeline. Returns (response payload, comparison id)."""
    resolved_zone, zone_db_value = resolve_zone(zone)

    # ── Query brain knowledge entries ──
    doc_entry = await db.execute(
        select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == "tender_document",
            KnowledgeEntry.tender_id == tender_id,
        ).order_by(KnowledgeEntry.created_at.desc()).limit(1)
    )
    doc_entry = doc_entry.scalar_one_or_none()
    if not doc_entry:
        raise BOQCompareError(f"No tender_document knowledge found for tender {tender_id}")

    boq_entry = await db.execute(
        select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == "boq_text",
            KnowledgeEntry.tender_id == tender_id,
        ).order_by(KnowledgeEntry.created_at.desc()).limit(1)
    )
    boq_entry = boq_entry.scalar_one_or_none()

    tds_entry = await db.execute(
        select(KnowledgeEntry).where(
            KnowledgeEntry.entry_type == "tds_text",
            KnowledgeEntry.tender_id == tender_id,
        ).order_by(KnowledgeEntry.created_at.desc()).limit(1)
    )
    tds_entry = tds_entry.scalar_one_or_none()

    # ── Build tender_info from brain knowledge ──
    doc_data = doc_entry.data or {}
    tender_info = doc_data.get("tender_info", {})
    tender_info_dict = dict(tender_info) if tender_info else {}
    tender_info_dict.setdefault("tender_id", tender_id)
    tender_info_dict.setdefault("title", doc_data.get("title") or doc_entry.title or "")
    tender_info_dict.setdefault("entity", tender_info_dict.get("procuring_entity") or doc_data.get("procuring_entity", ""))
    package_no = tender_info_dict.get("package_no") or doc_data.get("package_no") or ""
    tender_info_dict["package_no"] = package_no

    # ── Find BOQ PDF from downloaded_files in brain knowledge ──
    downloaded_files = doc_data.get("downloaded_files", []) or []
    boq_pdf = None
    for f in downloaded_files:
        fp = f.get("path", "")
        kind = (f.get("kind") or f.get("doc_type") or "").lower()
        fname_lower = Path(fp).name.lower() + " " + str(fp).lower()
        if "boq" in kind or "bill" in kind or "quantity" in kind or "section6" in fname_lower:
            if Path(fp).exists():
                boq_pdf = fp
                break

    if not boq_pdf:
        storage_dir = doc_data.get("storage_dir") or doc_data.get("download_path") or ""
        if storage_dir and Path(storage_dir).is_dir():
            for f in Path(storage_dir).rglob("*.pdf"):
                fname = f.name.lower()
                if "boq" in fname or "bill" in fname or "quantity" in fname or "section6" in fname:
                    boq_pdf = str(f)
                    break

    # Older acquisition records did not always persist storage_dir/downloaded_files,
    # even though their artifacts were mirrored into backend/uploads/{tender_id}.
    # Treat that canonical tender directory as the final source of truth.
    if not boq_pdf and Path(tender_id).name == tender_id:
        backend_root = Path(__file__).resolve().parents[2]
        tender_upload_dir = backend_root / "uploads" / tender_id
        if tender_upload_dir.is_dir():
            preferred = tender_upload_dir / "boq.pdf"
            if preferred.is_file():
                boq_pdf = str(preferred)
            else:
                for f in tender_upload_dir.rglob("*.pdf"):
                    searchable = f"{f.name} {f.parent.name}".lower()
                    if (
                        "boq" in searchable
                        or "bill of quantit" in searchable
                        or "section6" in searchable
                        or "section6_" in searchable
                    ):
                        boq_pdf = str(f)
                        break

    if not boq_pdf:
        raise BOQCompareError(f"BOQ PDF not found in brain knowledge for tender {tender_id}")

    # ── Lookup APP Estimated Cost by package number ──
    tender_info_dict["estimated_cost_app"] = await _lookup_app_estimate(db, package_no)

    # ── Extract TDS financial criteria from brain knowledge ──
    tds_text = (tds_entry.data or {}).get("text", "") if tds_entry else ""
    if tds_text:
        try:
            financial_check = extract_tds_criteria(tds_text)
            if financial_check:
                tender_info_dict["financial_check"] = financial_check
        except Exception:
            pass

    # ── Run BOQ comparison ──
    from app.services.boq_processor import BOQProcessor
    from app.sor.sor_service import sor_service

    processor = BOQProcessor()
    result = await processor.compare(
        boq_path=str(boq_pdf),
        sor_agency=sor_agency,
        zone=resolved_zone,
        sor_service=sor_service,
        tender_info=tender_info_dict,
    )

    result["comparison_id"] = f"brain-{tender_id}"
    result["sor_agency"] = "BWDB / PWD / LGED"
    result["zone"] = zone
    result["created_at"] = datetime.now(timezone.utc).isoformat()
    result["source"] = "brain"

    tender_title = str(
        tender_info_dict.get("title")
        or doc_data.get("title")
        or f"BOQ from brain {tender_id}"
    ).strip() or f"BOQ Analysis {tender_id}"
    procuring_entity = str(
        tender_info_dict.get("entity")
        or tender_info_dict.get("procuring_entity")
        or sor_agency
    ).strip() or sor_agency

    comparison = await _persist_comparison(
        db,
        result=result,
        tender_info_dict=tender_info_dict,
        user_id=user_id,
        tender_public_id=tender_id,
        tender_title=tender_title,
        procuring_entity=procuring_entity,
        zone_db_value=zone_db_value,
        boq_file_id=f"brain-{tender_id}",
    )

    response = {
        **result,
        "financial_check": tender_info_dict.get("financial_check", []),
        "estimated_cost_app": tender_info_dict.get("estimated_cost_app"),
        "tender_notice": {
            "tender_id": tender_id,
            "title": tender_title,
            "procuring_entity": procuring_entity,
            "package_no": package_no,
            "downloaded_files": len(downloaded_files),
            "has_boq_text": boq_entry is not None,
            "has_tds_text": tds_entry is not None,
        },
    }
    return response, comparison.id
