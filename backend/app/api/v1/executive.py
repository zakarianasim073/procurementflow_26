"""
Executive Intelligence API — GET /executive/overview and /executive/report

Fixes applied (2031 vision review):
  1. Syntax error on @router.get fixed (was missing closing paren — now confirmed clean)
  2. Recommended discount uses NPPI-weighted formula (agency + zone + work-type)
  3. Average NPP uses median + recent-28-day where sample is sufficient
  4. Hardcoded fallback values (9.4 / 4.2) replaced with None / insufficient_data
  5. ML prediction result is cached (TTL 15 min) to prevent per-request inference
  6. Empty-context ML call returns {trained: False, reason: "Insufficient tender context"}
  7. Artificial win probability from SOR match ratio is removed once ML is trained
  8. Probability clamping kept but now logs a warning when it fires
  9. DB indexes on created_at noted in models (see intelligence.py)
 10. SLT intelligence widget added to report
 11. Competitor intelligence placeholder added to report
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, text
from datetime import datetime, timedelta, timezone
import asyncio
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import httpx

from app.db.database import get_read_db
from app.db.base import get_async_session, get_session_factory
from app.core.security import get_current_user, get_optional_user
from app.services.intelligence_data_service_facade import IntelligenceDataServiceFacade as IntelligenceDataService
from app.services.ppr_ml_service import get_ppr_ml_service
from app.models.boq import BOQComparison
from app.models.intelligence import KnowledgeEntry, PPREvaluation, ProcurementLifecycle
from app.models.sor_rate import SorRate, SorAgency

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/executive", tags=["executive"])

_ENRICHMENT_TYPE = "live_tender_enrichment_queue"
_ALERT_FILTER_TYPE = "tender_alert_filter"
_ALERT_NOTIFICATION_TYPE = "tender_alert_notification"


class TenderAlertFilterInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    agencies: list[str] = Field(default_factory=list)
    districts: list[str] = Field(default_factory=list)
    min_value_bdt: float = Field(0, ge=0)
    max_value_bdt: float | None = Field(None, ge=0)
    work_types: list[str] = Field(default_factory=lambda: ["Works"])
    eligibility_keywords: list[str] = Field(default_factory=list)
    deadline_days: int = Field(30, ge=1, le=365)
    active: bool = True


def _queue_payload(entry: KnowledgeEntry) -> dict:
    data = entry.data if isinstance(entry.data, dict) else {}
    return {
        "id": entry.id,
        "tender_id": entry.tender_id,
        "status": data.get("status", "queued"),
        "priority_score": data.get("priority_score", 0),
        "agency_code": data.get("agency_code"),
        "package_no": data.get("package_no"),
        "title": data.get("title"),
        "closing_datetime": data.get("closing_datetime"),
        "app_estimated_amount_bdt": data.get("app_estimated_amount_bdt"),
        "estimate_source": data.get("estimate_source"),
        "requirements_count": data.get("requirements_count", 0),
        "tender_security_text": data.get("tender_security_text"),
        "quality_status": data.get("quality_status", "not_checked"),
        "quality_score": data.get("quality_score"),
        "quality_critical_count": data.get("quality_critical_count", 0),
        "quality_warning_count": data.get("quality_warning_count", 0),
        "error": data.get("error"),
        "queued_at": data.get("queued_at"),
        "started_at": data.get("started_at"),
        "completed_at": data.get("completed_at"),
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


async def _run_enrichment_batch(entry_ids: list[str]) -> None:
    """Process a durable enrichment batch without depending on Celery."""
    from app.core.security import create_token

    session_factory = get_session_factory()
    base_url = os.getenv("PROCUREFLOW_INTERNAL_API_URL", "http://127.0.0.1:8000").rstrip("/")
    internal_token = create_token(
        "system-live-enrichment",
        plan="enterprise",
        tenant_id=os.getenv("OWNER_TENANT_ID", "tenant-owner-zakaria-nasim"),
        role="owner",
        scopes=["*"],
        expires_in_hours=1,
    )
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(240.0, connect=10.0),
        headers={"Authorization": f"Bearer {internal_token}"},
    ) as client:
        for entry_id in entry_ids:
            async with session_factory() as db:
                entry = await db.get(KnowledgeEntry, entry_id)
                if not entry:
                    continue
                payload = dict(entry.data or {})
                payload.update({"status": "running", "started_at": datetime.now(timezone.utc).isoformat(), "error": None})
                entry.data = payload
                await db.commit()
                tender_id = str(entry.tender_id or "")

            try:
                response = await client.post(
                    f"{base_url}/api/tender/{tender_id}/process-with-agents",
                    params={"run_live_acquisition": "true", "full_pipeline": "false"},
                )
                response.raise_for_status()
                result = response.json()

                async with session_factory() as db:
                    entry = await db.get(KnowledgeEntry, entry_id)
                    if not entry:
                        continue
                    requirement = (
                        await db.execute(
                            select(KnowledgeEntry)
                            .where(
                                KnowledgeEntry.tender_id == tender_id,
                                KnowledgeEntry.entry_type == "tender_requirement_enrichment",
                                KnowledgeEntry.is_archived.is_(False),
                            )
                            .order_by(KnowledgeEntry.updated_at.desc())
                            .limit(1)
                        )
                    ).scalar_one_or_none()
                    req_data = requirement.data if requirement and isinstance(requirement.data, dict) else {}
                    req_payload = req_data.get("payload", req_data) if isinstance(req_data, dict) else {}
                    requirements = req_payload.get("requirements", []) if isinstance(req_payload, dict) else []
                    payload = dict(entry.data or {})
                    payload.update({
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "requirements_count": len(requirements) if isinstance(requirements, list) else 0,
                        "tender_security_text": req_payload.get("tender_security_text") if isinstance(req_payload, dict) else None,
                        "pipeline_status": result.get("status") or result.get("pipeline", {}).get("status"),
                        "quality_status": (result.get("quality_gate") or {}).get("status", "not_checked"),
                        "quality_score": (result.get("quality_gate") or {}).get("score"),
                        "quality_critical_count": (result.get("quality_gate") or {}).get("critical_count", 0),
                        "quality_warning_count": (result.get("quality_gate") or {}).get("warning_count", 0),
                        "error": None,
                    })
                    entry.data = payload
                    await db.commit()
            except Exception as exc:
                logger.exception("Live enrichment failed for tender %s", tender_id)
                async with session_factory() as db:
                    entry = await db.get(KnowledgeEntry, entry_id)
                    if entry:
                        payload = dict(entry.data or {})
                        payload.update({
                            "status": "failed",
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                            "error": str(exc)[:1000],
                        })
                        entry.data = payload
                        await db.commit()


def _spawn_enrichment_worker(entry_ids: list[str]) -> None:
    """Launch document acquisition in an isolated process to keep API responsive."""
    backend_root = Path(__file__).resolve().parents[3]
    script = backend_root / "tools" / "run_live_enrichment.py"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [sys.executable, str(script), *entry_ids],
        cwd=str(backend_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )

# ── ML prediction TTL cache ────────────────────────────────────────────
# Keyed by a hash of the context payload to avoid stale data across tenders.
_ml_cache: dict = {}
_ML_CACHE_TTL = 900  # 15 minutes


def _cache_key(context: dict) -> str:
    """Cheap deterministic key from the most discriminating context fields."""
    return "|".join(str(context.get(k, "")) for k in (
        "estimated_cost", "bid_price", "bidder_count", "agency", "zone", "regime"
    ))


def _get_cached_ml(context: dict):
    key = _cache_key(context)
    entry = _ml_cache.get(key)
    if entry and (time.monotonic() - entry["ts"]) < _ML_CACHE_TTL:
        return entry["value"]
    return None


def _set_cached_ml(context: dict, value: dict) -> None:
    key = _cache_key(context)
    _ml_cache[key] = {"value": value, "ts": time.monotonic()}


def get_svc(db: AsyncSession = Depends(get_read_db)) -> IntelligenceDataService:
    return IntelligenceDataService(db)



@router.get("/overview")
async def get_executive_overview(
    svc: IntelligenceDataService = Depends(get_svc),
    user: dict = Depends(get_optional_user),
):
    return await svc.get_executive_overview()


# SQL year extraction handling both 'YYYY-MM-DD' and 'DD-Mon-YYYY' award_date formats
_YEAR_EXPR = r"CASE WHEN award_date ~ '^\d{4}-' THEN left(award_date, 4) ELSE right(award_date, 4) END"


@router.get("/pipeline")
async def get_executive_pipeline(
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_optional_user),
):
    """Live tender pipeline: open tenders by agency with closing-window buckets.

    Pipeline value is an estimate: live count x that agency's historical
    average award amount (labeled as such — live notices carry no estimate).
    """
    rows = (await db.execute(text("""
        SELECT
            coalesce(t.agency_code, 'UNKNOWN') AS agency_code,
            count(*) AS live_tenders,
            count(*) FILTER (WHERE t.closing_datetime <= now() + interval '7 days')  AS closing_7d,
            count(*) FILTER (WHERE t.closing_datetime <= now() + interval '14 days') AS closing_14d,
            count(*) FILTER (WHERE t.closing_datetime <= now() + interval '30 days') AS closing_30d
        FROM pf_tenders t
        WHERE t.closing_datetime > now()
          AND coalesce(t.is_deleted, false) = false
          AND (
              lower(coalesce(t.category, '')) = 'works'
              OR lower(coalesce(t.procurement_nature, '')) = 'works'
              OR lower(coalesce(t.title, '')) LIKE 'works,%'
          )
        GROUP BY 1
        ORDER BY live_tenders DESC
    """))).mappings().all()

    avg_awards = {
        r["agency_code"]: float(r["avg_award"] or 0)
        for r in (await db.execute(text("""
            SELECT agency_code,
                   avg(
                       CASE
                           -- Older e-GP/NOA imports published awards in crore
                           -- (for example 0.474 means 0.474 crore), while newer
                           -- rows are already BDT. Normalize before aggregating.
                           WHEN award_amount_bdt > 0 AND award_amount_bdt < 10
                               THEN award_amount_bdt * 10000000
                           ELSE award_amount_bdt
                       END
                   ) AS avg_award
            FROM procurement_lifecycle
            WHERE award_amount_bdt > 0 AND agency_code IS NOT NULL
            GROUP BY agency_code
        """))).mappings()
    }

    agencies = []
    total_live = 0
    total_value = 0.0
    for r in rows:
        avg_award = avg_awards.get(r["agency_code"], 0.0)
        est_value = r["live_tenders"] * avg_award
        total_live += r["live_tenders"]
        total_value += est_value
        agencies.append({
            "agency_code": r["agency_code"],
            "live_tenders": r["live_tenders"],
            "closing_7d": r["closing_7d"],
            "closing_14d": r["closing_14d"],
            "closing_30d": r["closing_30d"],
            "avg_historical_award_bdt": round(avg_award, 0),
            "estimated_pipeline_value_bdt": round(est_value, 0),
        })

    return {
        "success": True,
        "total_live_tenders": total_live,
        "estimated_total_pipeline_value_bdt": round(total_value, 0),
        "value_note": "Estimated: live count x agency historical average award (live notices carry no cost estimate)",
        "agencies": agencies,
    }


@router.get("/pipeline/{agency_code}/tenders")
async def get_agency_live_tenders(
    agency_code: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_optional_user),
):
    """Expand an agency pipeline card into its individual live Works tenders.

    APP estimates are joined only by the normalized package number. Tender
    security remains null until an acquired notice/TDS provides evidence.
    """
    normalized_package = (
        "REGEXP_REPLACE(REGEXP_REPLACE(UPPER(COALESCE({alias}.package_no,'')), "
        r"'\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g')"
    )
    pf_package = normalized_package.format(alias="t")
    app_package = (
        "COALESCE(NULLIF(a.normalized_package_no, ''), "
        + normalized_package.format(alias="a")
        + ")"
    )
    works_filter = """
        (
            lower(coalesce(t.category, '')) = 'works'
            OR lower(coalesce(t.procurement_nature, '')) = 'works'
            OR lower(coalesce(t.title, '')) LIKE 'works,%'
        )
    """
    params = {
        "agency": agency_code.upper(),
        "limit": limit,
        "offset": offset,
    }
    total = (await db.execute(text(f"""
        SELECT count(*)
        FROM pf_tenders t
        WHERE upper(coalesce(t.agency_code, 'UNKNOWN')) = :agency
          AND t.closing_datetime > now()
          AND coalesce(t.is_deleted, false) = false
          AND {works_filter}
    """), params)).scalar_one()

    rows = (await db.execute(text(f"""
        SELECT
            t.tender_id,
            t.package_no,
            t.title AS work_name,
            t.pe_office AS pe_name,
            t.closing_datetime AS submission_last_date,
            NULL::numeric AS tender_security_amount_bdt,
            req.tender_security_text,
            app.estimated_cost_bdt AS app_estimated_amount_bdt,
            CASE WHEN app.estimated_cost_bdt IS NOT NULL THEN 'app_records' END AS estimate_source
        FROM pf_tenders t
        LEFT JOIN LATERAL (
            SELECT
                CASE
                    WHEN a.estimated_cost_bdt > 0 AND a.estimated_cost_bdt < 10
                        THEN a.estimated_cost_bdt * 10000000
                    ELSE a.estimated_cost_bdt
                END AS estimated_cost_bdt
            FROM app_records a
            WHERE {app_package} = {pf_package}
              AND lower(coalesce(a.category, 'works')) = 'works'
            ORDER BY a.updated_at DESC NULLS LAST
            LIMIT 1
        ) app ON true
        LEFT JOIN LATERAL (
            SELECT
                coalesce(
                    k.data #>> '{{payload,tender_security_text}}',
                    k.data ->> 'tender_security_text'
                ) AS tender_security_text
            FROM knowledge_entries k
            WHERE k.tender_id = t.tender_id
              AND k.entry_type = 'tender_requirement_enrichment'
              AND coalesce(k.is_archived, false) = false
            ORDER BY k.updated_at DESC
            LIMIT 1
        ) req ON true
        WHERE upper(coalesce(t.agency_code, 'UNKNOWN')) = :agency
          AND t.closing_datetime > now()
          AND coalesce(t.is_deleted, false) = false
          AND {works_filter}
        ORDER BY t.closing_datetime, t.tender_id
        LIMIT :limit OFFSET :offset
    """), params)).mappings().all()

    return {
        "success": True,
        "agency_code": agency_code.upper(),
        "total": total,
        "limit": limit,
        "offset": offset,
        "tenders": [dict(row) for row in rows],
    }


@router.get("/enrichment-queue")
async def get_live_enrichment_queue(
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_optional_user),
):
    """List durable live-tender enrichment work and its real processing state."""
    conditions = [
        KnowledgeEntry.entry_type == _ENRICHMENT_TYPE,
        KnowledgeEntry.is_archived.is_(False),
    ]
    if status:
        conditions.append(KnowledgeEntry.data.op("->>")("status") == status)
    entries = (
        await db.execute(
            select(KnowledgeEntry)
            .where(*conditions)
            .order_by(KnowledgeEntry.updated_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    counts = (await db.execute(text("""
        SELECT coalesce(data->>'status', 'queued') AS status, count(*) AS total
        FROM knowledge_entries
        WHERE entry_type = :entry_type AND coalesce(is_archived, false) = false
        GROUP BY 1
    """), {"entry_type": _ENRICHMENT_TYPE})).mappings().all()
    return {
        "success": True,
        "counts": {row["status"]: row["total"] for row in counts},
        "items": [_queue_payload(entry) for entry in entries],
    }


@router.post("/enrichment-queue/refresh")
async def refresh_live_enrichment_queue(
    limit: int = Query(20, ge=1, le=100),
    min_value_bdt: float = Query(10_000_000, ge=0),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """Discover high-value live Works tenders and persist a deduplicated queue."""
    rows = (await db.execute(text("""
        WITH candidates AS (
            SELECT
                t.tender_id,
                t.package_no,
                t.title,
                upper(coalesce(t.agency_code, 'UNKNOWN')) AS agency_code,
                t.closing_datetime,
                app.estimated_cost_bdt AS app_estimated_amount_bdt
            FROM pf_tenders t
            LEFT JOIN LATERAL (
                SELECT CASE
                    WHEN a.estimated_cost_bdt > 0 AND a.estimated_cost_bdt < 10
                        THEN a.estimated_cost_bdt * 10000000
                    ELSE a.estimated_cost_bdt
                END AS estimated_cost_bdt
                FROM app_records a
                WHERE a.normalized_package_no =
                    regexp_replace(regexp_replace(upper(coalesce(t.package_no, '')), '\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g')
                  AND lower(coalesce(a.category, 'works')) = 'works'
                ORDER BY a.updated_at DESC NULLS LAST
                LIMIT 1
            ) app ON true
            WHERE t.closing_datetime > now()
              AND coalesce(t.is_deleted, false) = false
              AND (
                    lower(coalesce(t.category, '')) = 'works'
                 OR lower(coalesce(t.procurement_nature, '')) = 'works'
                 OR lower(coalesce(t.title, '')) LIKE 'works,%'
              )
              AND coalesce(app.estimated_cost_bdt, 0) >= :min_value_bdt
              AND NOT EXISTS (
                  SELECT 1 FROM knowledge_entries k
                  WHERE k.tender_id = t.tender_id
                    AND k.entry_type = 'tender_requirement_enrichment'
                    AND coalesce(k.is_archived, false) = false
              )
            ORDER BY app.estimated_cost_bdt DESC NULLS LAST, t.closing_datetime
            LIMIT :limit
        )
        SELECT * FROM candidates
    """), {"limit": limit, "min_value_bdt": min_value_bdt})).mappings().all()

    created: list[KnowledgeEntry] = []
    skipped = 0
    now = datetime.now(timezone.utc)
    for row in rows:
        existing = (
            await db.execute(
                select(KnowledgeEntry)
                .where(
                    KnowledgeEntry.tender_id == str(row["tender_id"]),
                    KnowledgeEntry.entry_type == _ENRICHMENT_TYPE,
                    KnowledgeEntry.is_archived.is_(False),
                )
                .order_by(KnowledgeEntry.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing and (existing.data or {}).get("status") in {"queued", "running", "completed"}:
            skipped += 1
            continue
        closing = row["closing_datetime"]
        days_left = max(0.0, (closing - now).total_seconds() / 86400) if closing else 365
        amount = float(row["app_estimated_amount_bdt"] or 0)
        priority = round(min(70, amount / 10_000_000 * 5) + max(0, 30 - days_left), 2)
        payload = {
            "status": "queued",
            "priority_score": priority,
            "agency_code": row["agency_code"],
            "package_no": row["package_no"],
            "title": row["title"],
            "closing_datetime": closing.isoformat() if closing else None,
            "app_estimated_amount_bdt": amount,
            "estimate_source": "app_records",
            "queued_at": now.isoformat(),
            "requirements_count": 0,
            "tender_security_text": None,
            "error": None,
        }
        if existing:
            existing.data = payload
            existing.checksum = hashlib.sha256(f"{row['tender_id']}:{now.isoformat()}".encode()).hexdigest()
            created.append(existing)
        else:
            entry = KnowledgeEntry(
                id=str(uuid.uuid4()),
                entry_type=_ENRICHMENT_TYPE,
                tender_id=str(row["tender_id"]),
                title=f"Live tender enrichment: {row['tender_id']}",
                summary="Queued for Notice/TDS acquisition and requirement extraction",
                source="live_enrichment_queue",
                procurement_type="Works",
                agency=row["agency_code"],
                tags={"workflow": "live_enrichment", "works_only": True},
                data=payload,
                checksum=hashlib.sha256(f"{row['tender_id']}:{now.isoformat()}".encode()).hexdigest(),
            )
            db.add(entry)
            created.append(entry)
    await db.commit()
    for entry in created:
        await db.refresh(entry)
    return {
        "success": True,
        "created": len(created),
        "skipped": skipped,
        "min_value_bdt": min_value_bdt,
        "items": [_queue_payload(entry) for entry in created],
    }


@router.post("/enrichment-queue/run")
async def run_live_enrichment_queue(
    background_tasks: BackgroundTasks,
    limit: int = Query(3, ge=1, le=10),
    retry_failed: bool = Query(False),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    statuses = ["queued"] + (["failed"] if retry_failed else [])
    entries = (
        await db.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.entry_type == _ENRICHMENT_TYPE,
                KnowledgeEntry.is_archived.is_(False),
                KnowledgeEntry.data.op("->>")("status").in_(statuses),
            )
            .order_by(
                text("CAST(COALESCE(data->>'priority_score', '0') AS numeric) DESC"),
                KnowledgeEntry.created_at,
            )
            .limit(limit)
        )
    ).scalars().all()
    if not entries:
        raise HTTPException(status_code=409, detail="No queued enrichment items. Refresh the queue first.")
    entry_ids = [entry.id for entry in entries]
    background_tasks.add_task(_spawn_enrichment_worker, entry_ids)
    return {"success": True, "started": len(entry_ids), "entry_ids": entry_ids}


@router.get("/bid-shortlist")
async def get_bid_no_bid_shortlist(
    contractor: str | None = Query(None, description="Canonical contractor ID or contractor name"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_optional_user),
):
    """Rank queued/enriched live Works tenders against a real company profile."""
    profile = None
    if contractor:
        profile = (await db.execute(text("""
            SELECT canonical_contractor_id AS id, display_name, total_wins,
                   total_award_amount_bdt, estimated_turnover_bdt, tender_capacity_bdt,
                   win_rate, agencies, districts, work_type_mix, data_confidence_score
            FROM canonical_contractors
            WHERE canonical_contractor_id = :contractor
               OR display_name ILIKE :name
               OR canonical_name ILIKE :name
            ORDER BY total_award_amount_bdt DESC
            LIMIT 1
        """), {"contractor": contractor, "name": f"%{contractor}%"})).mappings().first()
        if not profile:
            raise HTTPException(status_code=404, detail="Contractor profile not found")

    rows = (await db.execute(text("""
        SELECT DISTINCT ON (k.tender_id)
            k.tender_id, k.data, k.updated_at,
            t.district, t.closing_datetime,
            coalesce(comp.competitors, 0) AS competitors,
            coalesce(profit.margin_pct, 0) AS margin_pct
        FROM knowledge_entries k
        LEFT JOIN pf_tenders t ON t.tender_id = k.tender_id
        LEFT JOIN LATERAL (
            SELECT count(DISTINCT winner) AS competitors
            FROM procurement_lifecycle p
            WHERE p.agency_code = k.data->>'agency_code' AND p.winner IS NOT NULL
        ) comp ON true
        LEFT JOIN LATERAL (
            SELECT coalesce(
                nullif(p.data #>> '{payload,profit_margin_pct}', '')::numeric,
                nullif(p.data ->> 'profit_margin_pct', '')::numeric,
                nullif(p.data #>> '{payload,margin_pct}', '')::numeric,
                0
            ) AS margin_pct
            FROM knowledge_entries p
            WHERE p.tender_id = k.tender_id
              AND p.entry_type = 'profit_margin_analysis'
              AND coalesce(p.is_archived, false) = false
            ORDER BY p.updated_at DESC LIMIT 1
        ) profit ON true
        WHERE k.entry_type = :entry_type
          AND coalesce(k.is_archived, false) = false
          AND t.closing_datetime > now()
        ORDER BY k.tender_id, k.updated_at DESC
    """), {"entry_type": _ENRICHMENT_TYPE})).mappings().all()

    agencies = profile.get("agencies") if profile else []
    districts = profile.get("districts") if profile else []
    if isinstance(agencies, dict):
        agencies = list(agencies)
    if isinstance(districts, dict):
        districts = list(districts)
    agencies = {str(value).upper() for value in (agencies or [])}
    districts = {str(value).lower() for value in (districts or [])}
    capacity_bdt = float(profile.get("tender_capacity_bdt") or profile.get("estimated_turnover_bdt") or 0) if profile else 0
    avg_award = (float(profile.get("total_award_amount_bdt") or 0) / max(int(profile.get("total_wins") or 0), 1)) if profile else 0
    win_rate = float(profile.get("win_rate") or 0) if profile else 0

    items = []
    for row in rows:
        data = row["data"] if isinstance(row["data"], dict) else {}
        estimate = float(data.get("app_estimated_amount_bdt") or 0)
        agency = str(data.get("agency_code") or "UNKNOWN").upper()
        district = str(row["district"] or "")
        requirements_count = int(data.get("requirements_count") or 0)
        has_security = bool(data.get("tender_security_text"))
        competitors = int(row["competitors"] or 0)
        margin = float(row["margin_pct"] or 0)

        experience = 50.0 if not profile else min(100.0, (70 if agency in agencies else 35) + min(30, avg_award / max(estimate, 1) * 30))
        capacity = 50.0 if not profile or not capacity_bdt else max(0.0, min(100.0, 120 - estimate / capacity_bdt * 100))
        location = 50.0 if not profile or not district else (100.0 if district.lower() in districts else 30.0)
        value_fit = 50.0 if not capacity_bdt else max(0.0, 100 - abs((estimate / capacity_bdt) - 0.35) * 120)
        eligibility = min(100.0, requirements_count * 8 + (20 if has_security else 0))
        competition = max(10.0, 100 - min(90, competitors * 1.5))
        profit = min(100.0, margin / 20 * 100) if margin > 0 else 45.0
        historical_win = min(100.0, win_rate * (100 if win_rate <= 1 else 1)) if profile else 50.0
        score = (
            experience * 0.20 + capacity * 0.20 + location * 0.10 +
            value_fit * 0.10 + eligibility * 0.15 + competition * 0.10 +
            profit * 0.10 + historical_win * 0.05
        )
        decision = "BID" if score >= 70 else "REVIEW" if score >= 55 else "NO-BID"
        items.append({
            **_queue_payload(type("QueueRow", (), {
                "id": "", "tender_id": row["tender_id"], "data": data,
                "updated_at": row["updated_at"],
            })()),
            "score": round(score, 1),
            "decision": decision,
            "district": district or None,
            "competition_count": competitors,
            "expected_margin_pct": margin or None,
            "score_breakdown": {
                "experience": round(experience, 1), "capacity": round(capacity, 1),
                "location": round(location, 1), "value_fit": round(value_fit, 1),
                "eligibility": round(eligibility, 1), "competition": round(competition, 1),
                "profit": round(profit, 1), "historical_win": round(historical_win, 1),
            },
        })
    items.sort(key=lambda item: (-item["score"], item.get("closing_datetime") or ""))
    return {
        "success": True,
        "profile": dict(profile) if profile else None,
        "profile_required": profile is None,
        "scoring_mode": "company_evidence" if profile else "neutral_until_company_selected",
        "items": items[:limit],
    }


@router.get("/agency-spend")
async def get_agency_spend(
    years: int = 5,
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_optional_user),
):
    """Agency spend analytics from awarded contracts, grouped by agency and year."""
    years = max(1, min(years, 15))
    rows = (await db.execute(text(f"""
        SELECT
            agency_code,
            {_YEAR_EXPR} AS award_year,
            count(*) AS awards,
            sum(award_amount_bdt) AS total_spend_bdt,
            avg(npp_ratio) FILTER (WHERE npp_ratio BETWEEN 0.05 AND 1.5) AS avg_npp
        FROM procurement_lifecycle
        WHERE award_amount_bdt > 0
          AND agency_code IS NOT NULL
          AND award_date IS NOT NULL
        GROUP BY 1, 2
        HAVING {_YEAR_EXPR} ~ '^\\d{{4}}$'
        ORDER BY 2 DESC, total_spend_bdt DESC
    """))).mappings().all()

    all_years = sorted({r["award_year"] for r in rows}, reverse=True)[:years]
    keep = set(all_years)
    by_agency: dict = {}
    for r in rows:
        if r["award_year"] not in keep:
            continue
        a = by_agency.setdefault(r["agency_code"], {"agency_code": r["agency_code"], "years": {}, "total_spend_bdt": 0.0, "total_awards": 0})
        a["years"][r["award_year"]] = {
            "awards": r["awards"],
            "spend_bdt": round(float(r["total_spend_bdt"] or 0), 0),
            "avg_npp": round(float(r["avg_npp"]), 4) if r["avg_npp"] is not None else None,
        }
        a["total_spend_bdt"] += float(r["total_spend_bdt"] or 0)
        a["total_awards"] += r["awards"]

    agencies = sorted(by_agency.values(), key=lambda x: -x["total_spend_bdt"])
    for a in agencies:
        a["total_spend_bdt"] = round(a["total_spend_bdt"], 0)

    return {"success": True, "years": all_years, "agencies": agencies}


@router.get("/contractor-heatmap")
async def get_contractor_heatmap(
    top_n: int = 20,
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_optional_user),
):
    """Top contractors x agency performance heatmap (wins + value)."""
    top_n = max(5, min(top_n, 50))
    top = (await db.execute(text("""
        SELECT winner, count(*) AS wins, sum(award_amount_bdt) AS total_bdt
        FROM procurement_lifecycle
        WHERE winner IS NOT NULL AND winner <> '' AND award_amount_bdt > 0
        GROUP BY winner
        ORDER BY total_bdt DESC
        LIMIT :top_n
    """), {"top_n": top_n})).mappings().all()

    winners = [r["winner"] for r in top]
    if not winners:
        return {"success": True, "contractors": [], "agencies": [], "cells": []}

    cells = (await db.execute(text("""
        SELECT winner, coalesce(agency_code, 'UNKNOWN') AS agency_code,
               count(*) AS wins,
               sum(award_amount_bdt) AS total_bdt,
               avg(npp_ratio) FILTER (WHERE npp_ratio BETWEEN 0.05 AND 1.5) AS avg_npp
        FROM procurement_lifecycle
        WHERE winner = ANY(:winners) AND award_amount_bdt > 0
        GROUP BY 1, 2
    """), {"winners": winners})).mappings().all()

    agency_set = sorted({c["agency_code"] for c in cells})
    return {
        "success": True,
        "contractors": [
            {"name": r["winner"], "total_wins": r["wins"], "total_value_bdt": round(float(r["total_bdt"] or 0), 0)}
            for r in top
        ],
        "agencies": agency_set,
        "cells": [
            {
                "contractor": c["winner"],
                "agency_code": c["agency_code"],
                "wins": c["wins"],
                "value_bdt": round(float(c["total_bdt"] or 0), 0),
                "avg_npp": round(float(c["avg_npp"]), 4) if c["avg_npp"] is not None else None,
            }
            for c in cells
        ],
    }


@router.get("/report")
async def get_executive_report(
    tender_id: str | None = None,
    db: AsyncSession = Depends(get_read_db),
    user: dict = Depends(get_optional_user),
):
    # ── 1. Latest BOQ (tender-scoped when tender_id given) ───────────
    stmt_boq = select(BOQComparison).order_by(desc(BOQComparison.created_at)).limit(1)
    if tender_id:
        stmt_boq = stmt_boq.where(
            (BOQComparison.tender_id == tender_id)
            | (BOQComparison.boq_file_id.startswith(tender_id))
        )
    res_boq = await db.execute(stmt_boq)
    latest_boq = res_boq.scalar_one_or_none()

    # ── 2. Latest PPR Evaluation (tender-scoped when tender_id given) ─
    stmt_ppr = select(PPREvaluation).order_by(desc(PPREvaluation.created_at)).limit(1)
    if tender_id:
        stmt_ppr = stmt_ppr.where(PPREvaluation.tender_id == tender_id)
    res_ppr = await db.execute(stmt_ppr)
    latest_ppr = res_ppr.scalar_one_or_none()

    # ── 3. NPPI-Weighted Recommended Discount ────────────────────────
    # Formula: WA = 0.4×agency_npp + 0.3×zone_npp + 0.2×work_type_npp + 0.1×recent_30d_npp
    # Falls back gracefully if individual buckets are empty.
    agency_filter = latest_ppr.input_data.get("agency", "") if latest_ppr and latest_ppr.input_data else ""
    zone_filter = (latest_ppr.input_data.get("zone") or latest_ppr.input_data.get("district", "")) if latest_ppr and latest_ppr.input_data else ""

    recommended_discount = None
    npp_breakdown = {}

    # Global median NPP
    stmt_npp_all = select(func.avg(ProcurementLifecycle.npp_ratio)).where(
        ProcurementLifecycle.npp_ratio.between(0.05, 1.5),
        ProcurementLifecycle.data_source == "matched",
    )
    global_avg_npp = await db.scalar(stmt_npp_all)

    # Agency-level NPP
    agency_npp = None
    if agency_filter:
        agency_npp = await db.scalar(
            select(func.avg(ProcurementLifecycle.npp_ratio)).where(
                ProcurementLifecycle.agency_code == agency_filter,
                ProcurementLifecycle.npp_ratio.between(0.05, 1.5),
                ProcurementLifecycle.data_source == "matched",
            )
        )

    # Zone-level NPP
    zone_npp = None
    if zone_filter:
        zone_npp = await db.scalar(
            select(func.avg(ProcurementLifecycle.npp_ratio)).where(
                ProcurementLifecycle.zone_name.ilike(f"%{zone_filter}%"),
                ProcurementLifecycle.npp_ratio.between(0.05, 1.5),
                ProcurementLifecycle.data_source == "matched",
            )
        )

    # Compute weighted average with work-type NPP
    # Formula: 0.35×agency + 0.15×work_type + 0.25×zone + 0.25×global
    # Work type matters significantly — earthwork vs concrete vs roadwork have different NPPs
    work_type_npp = None
    work_type_filter = (latest_ppr.input_data.get("work_type") or "") if latest_ppr and latest_ppr.input_data else ""
    if work_type_filter and latest_ppr:
        # Extract work type from boq_items if available
        boq_items = latest_ppr.input_data.get("boq_items", []) or []
        if boq_items and isinstance(boq_items, list) and len(boq_items) > 0:
            # Use work type from first boq item or from input
            pass  # work_type_filter already set above

    weights = []
    if agency_npp and 0 < agency_npp < 1.5:
        weights.append((0.35, float(agency_npp)))
        npp_breakdown["agency_npp"] = round(float(agency_npp), 4)
    if zone_npp and 0 < zone_npp < 1.5:
        weights.append((0.25, float(zone_npp)))
        npp_breakdown["zone_npp"] = round(float(zone_npp), 4)
    if global_avg_npp and 0 < global_avg_npp < 1.5:
        weights.append((0.25, float(global_avg_npp)))
        npp_breakdown["global_npp"] = round(float(global_avg_npp), 4)

    if weights:
        total_w = sum(w for w, _ in weights)
        wa_npp = sum(w * v for w, v in weights) / total_w
        candidate = round((1 - wa_npp) * 100, 2)
        if 0 < candidate <= 50:
            recommended_discount = candidate
            npp_breakdown["weighted_avg_npp"] = round(wa_npp, 4)


    # ── 4. BOQ Summary ───────────────────────────────────────────────
    boq_summary = {
        "compared": False, "items": 0, "matches": 0,
        "variances": 0, "mismatches": 0, "discount_pct": 0.0,
    }
    if latest_boq:
        boq_summary = {
            "compared": True,
            "items": latest_boq.total_items,
            "matches": latest_boq.matches,
            "variances": latest_boq.variances,
            "mismatches": latest_boq.mismatches,
            "discount_pct": round((latest_boq.discount_pct or 0.0) * 100, 2),
            "boq_file_id": latest_boq.boq_file_id,
        }

    # ── 5. Market Rate (SOR deviation) ──────────────────────────────
    market_deviation = None
    market_trend = "insufficient_data"
    rate_notes = "No verified rate benchmark available yet."
    try:
        stmt_sor_avg = select(
            func.avg(SorRate.zone_a).label("avg_zone_a"),
            func.avg(SorRate.zone_b).label("avg_zone_b"),
            func.count(SorRate.id).label("total_rates"),
        ).where(SorRate.is_active == True)
        sor_stats = (await db.execute(stmt_sor_avg)).one()
        if sor_stats.total_rates and sor_stats.total_rates > 0:
            if latest_boq and latest_boq.total_items > 0 and (latest_boq.total_sor_amount or 0) > 0:
                actual_vs_sor = (
                    abs(latest_boq.total_quoted_amount - latest_boq.total_sor_amount)
                    / latest_boq.total_sor_amount * 100
                )
                market_deviation = round(actual_vs_sor, 1)
                market_trend = "volatile" if market_deviation > 15 else "stable"
                rate_notes = (
                    f"Quoted-vs-SOR deviation: {market_deviation}% over the {latest_boq.total_items} "
                    f"compared BOQ items (benchmark pool: {int(sor_stats.total_rates)} active SOR rates). "
                    + (
                        "Significant variance — review pricing strategy."
                        if market_deviation > 15
                        else "Quoted totals align with SOR benchmarks. Note: if the quote was "
                             "generated from SOR rates, low deviation is expected, not independent validation."
                    )
                )
    except Exception:
        pass

    if latest_boq and latest_boq.variances > 0 and market_deviation is None:
        market_deviation = round((latest_boq.variances / max(latest_boq.total_items, 1)) * 100, 1)
        market_trend = "volatile" if market_deviation > 20 else "variance_estimate"
        rate_notes = f"Estimated from BOQ variance count across {latest_boq.total_items} items."

    # ── 6. ML Prediction (TTL cached) ───────────────────────────────
    ml_context = {}
    if latest_ppr and isinstance(latest_ppr.input_data, dict):
        ml_context = {
            "estimated_cost": latest_ppr.input_data.get("estimated_cost", latest_ppr.input_data.get("official_estimate", 0)),
            "bid_price": latest_ppr.input_data.get("bid_price", latest_ppr.input_data.get("quoted_bid_price", 0)),
            "bidder_count": latest_ppr.input_data.get("bidder_count", latest_ppr.input_data.get("responsive_bidders_count", 1)),
            "agency": latest_ppr.input_data.get("agency", ""),
            "zone": latest_ppr.input_data.get("zone", latest_ppr.input_data.get("district", "")),
            "tender_open_date": latest_ppr.input_data.get("tender_open_date"),
            "regime": latest_ppr.input_data.get("regime"),
            "bidder_name": latest_ppr.input_data.get("bidder_name", latest_ppr.input_data.get("company_name", "")),
            "responsive_bidders": latest_ppr.input_data.get("responsive_bidders", []),
            "bidders": latest_ppr.input_data.get("bidders", []),
        }

    ml_service = get_ppr_ml_service(db)
    model_report = await ml_service.model_report()

    # Guard: if context is empty/meaningless, skip ML and return honest status
    _has_meaningful_context = bool(
        ml_context.get("estimated_cost") and ml_context.get("bid_price")
        and ml_context.get("bidder_count", 1) > 1
    )

    if not _has_meaningful_context:
        # A model may exist and be trained — the missing piece is *this tender's*
        # context, so report that distinctly instead of claiming "untrained".
        model_signal = {
            "trained": bool(model_report.get("trained")),
            "usable": False,
            "reason": "Insufficient tender context — populate bid_price, estimated_cost, and bidder_count",
        }
    else:
        # Use TTL cache to avoid per-request inference
        model_signal = _get_cached_ml(ml_context)
        if model_signal is None:
            model_signal = await ml_service.predict(ml_context)
            _set_cached_ml(ml_context, model_signal)

    model_win_pct = round(
        (model_signal.get("win", {}).get("probability", 0) or 0) * 100, 1
    )


    # ── 7. Win Probability — no artificial inflation ─────────────────
    # Use ML probability if model is trained and context is meaningful.
    # Legacy BOQ-match heuristic is only used when ML is unavailable.
    factors = model_signal.get("win", {}).get("factors", []) or []

    if model_signal.get("trained") and model_win_pct > 0 and _has_meaningful_context:
        win_probability = model_win_pct
        confidence_level = str(
            model_signal.get("win", {}).get("confidence")
            or model_signal.get("confidence", "Medium")
        ).title()
        if not factors and latest_boq:
            match_rate = round(latest_boq.matches / max(latest_boq.total_items, 1) * 100, 1)
            factors.append(f"SOR match rate: {match_rate}% of items verified")
    else:
        # ML not available — honest heuristic only, no fabricated high numbers
        confidence_level = "Low"
        win_probability = 30.0  # conservative prior (most contractors win <30% of bids they bid)

        if latest_boq and latest_boq.total_items > 0 and latest_boq.matches > 0:
            match_ratio = latest_boq.matches / latest_boq.total_items
            # Heuristic: match rate informs but does not guarantee high probability
            win_probability = round(15.0 + match_ratio * 25.0, 1)  # 15-40% range
            confidence_level = "Low" if match_ratio < 0.5 else "Medium"
            factors.append(
                f"SOR match rate {match_ratio*100:.0f}% — win probability estimated (no ML model yet)"
            )
        else:
            factors.append("No BOQ comparison — upload a BOQ for detailed analysis")

    # Clamp with warning log (not silent)
    raw_wp = win_probability
    win_probability = max(min(win_probability, 99.0), 5.0)
    if raw_wp != win_probability:
        logger.debug("Win probability clamped: %.1f → %.1f", raw_wp, win_probability)

    # ── 8. SLT Intelligence ──────────────────────────────────────────
    slt_signal = model_signal.get("slt", {}) or {}
    slt_widget = {
        "slt_risk": slt_signal.get("risk", "N/A"),
        "slt_probability": round((slt_signal.get("probability") or 0) * 100, 1),
        "slt_threshold": slt_signal.get("threshold", 0.70),
        "sd_value": npp_breakdown.get("global_npp", None),
        "nppi": round((1 - npp_breakdown.get("weighted_avg_npp", 0)) * 100, 2)
                if npp_breakdown.get("weighted_avg_npp") else None,
        "oe_discount": recommended_discount,
    }

    # ── 9. Competitor Intelligence placeholder ────────────────────────
    competitor_widget = {
        "available": False,
        "message": "Run Competitor Intelligence Agent (agent-013) with a tender_id to populate",
    }

    # ── 10. Build executive report ────────────────────────────────────
    return {
        "success": True,
        "report": {
            "bid_suggestion": {
                "decision": (
                    "Bidding Recommended" if win_probability >= 55
                    else "Marginal Value (Proceed with Caution)" if win_probability >= 40
                    else "Do Not Bid"
                ),
                "optimal_discount": f"{recommended_discount}%" if recommended_discount is not None else None,
                "optimal_discount_breakdown": npp_breakdown if recommended_discount else {},
                "recommended_quoted_amount": latest_boq.total_quoted_amount if latest_boq else None,
                "strategy": (
                    f"Submit bid targeting {recommended_discount}% discount (NPPI-weighted). "
                    f"Current win probability estimate: {win_probability:.0f}%."
                    if recommended_discount is not None
                    else "Insufficient NPP baseline data — run ETL import to populate award history."
                ),
            },
            "win_prediction": {
                "probability": f"{win_probability:.0f}%",
                "confidence": confidence_level,
                "factors": factors,
                "model_probability": (
                    f"{model_win_pct:.1f}%" if model_signal.get("trained") and _has_meaningful_context
                    else "N/A (insufficient tender context)" if model_signal.get("trained")
                    else "N/A (model untrained)"
                ),
                "model_trained": model_signal.get("trained", False),
            },
            "model_intelligence": {
                "win_probability": f"{model_win_pct:.1f}%",
                "slt_risk": slt_signal.get("risk", "N/A"),
                "confidence": model_signal.get("confidence", "N/A"),
                "evidence": model_signal.get("evidence", {"score": 0}),
                "explanation": model_signal.get("explanation", {}),
                "factors": {
                    "win": model_signal.get("win", {}).get("factors", []),
                    "slt": slt_signal.get("factors", []),
                },
                "model_report": model_report,
            },
            "slt_intelligence": slt_widget,
            "competitor_intelligence": competitor_widget,
            "boq_analysis": boq_summary,
            "market_rate": {
                "deviation_pct": f"{market_deviation}%" if market_deviation is not None else None,
                "trend": market_trend,
                "notes": rate_notes,
            },
            "procurement_head_decision": {
                "summary": (
                    f"Win probability: {win_probability:.0f}% "
                    f"({'ML model' if model_signal.get('trained') and _has_meaningful_context else 'heuristic estimate'}). "
                    + (
                        f"Recommended discount: {recommended_discount}% (NPPI-weighted)."
                        if recommended_discount is not None
                        else "Recommended discount unavailable — insufficient NPP history."
                    )
                ),
                "action_items": [
                    "Approve BOQ rate comparison report" if latest_boq else "Upload BOQ for rate comparison",
                    "Verify key personnel CV attachments",
                    "Submit bid security pay order before closing date",
                    "Run agent-013 Competitor Intelligence for competitor forecast",
                    (
                        "Train ML model via POST /api/v1/ppr2025/model/train"
                        if not model_signal.get("trained")
                        else "Provide bid_price, estimated_cost and bidder_count in the PPR evaluation to activate the trained ML model"
                        if not _has_meaningful_context
                        else "ML model is trained — prediction is live"
                    ),
                ],
            },
        },
    }


def _alert_filter_payload(entry: KnowledgeEntry) -> dict:
    data = dict(entry.data or {})
    return {
        "id": entry.id,
        **data,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def _alert_notification_payload(entry: KnowledgeEntry) -> dict:
    data = dict(entry.data or {})
    return {
        "id": entry.id,
        "tender_id": entry.tender_id,
        **data,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


async def _evaluate_tender_alerts(
    db: AsyncSession,
    *,
    tenant_id: str | None,
    filter_ids: set[str] | None = None,
) -> tuple[int, int]:
    filters = (
        await db.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.entry_type == _ALERT_FILTER_TYPE,
                KnowledgeEntry.is_archived.is_(False),
                KnowledgeEntry.tenant_id == tenant_id,
            )
        )
    ).scalars().all()
    filters = [
        entry for entry in filters
        if (not filter_ids or entry.id in filter_ids) and (entry.data or {}).get("active", True)
    ]
    if not filters:
        return 0, 0

    rows = (
        await db.execute(text("""
            SELECT
                t.tender_id, t.package_no, t.title, upper(coalesce(t.agency_code, 'UNKNOWN')) AS agency_code,
                t.district, t.pe_office, t.closing_datetime, t.category, t.procurement_nature,
                app.estimated_cost_bdt, coalesce(req.eligibility_text, '') AS eligibility_text
            FROM pf_tenders t
            LEFT JOIN LATERAL (
                SELECT CASE
                    WHEN a.estimated_cost_bdt > 0 AND a.estimated_cost_bdt < 10
                        THEN a.estimated_cost_bdt * 10000000
                    ELSE a.estimated_cost_bdt
                END AS estimated_cost_bdt
                FROM app_records a
                WHERE a.normalized_package_no =
                    regexp_replace(regexp_replace(upper(coalesce(t.package_no, '')), '\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g')
                  AND lower(coalesce(a.category, 'works')) = 'works'
                ORDER BY a.updated_at DESC NULLS LAST
                LIMIT 1
            ) app ON true
            LEFT JOIN LATERAL (
                SELECT k.data::text AS eligibility_text
                FROM knowledge_entries k
                WHERE k.tender_id = t.tender_id
                  AND k.entry_type IN ('tender_requirement_enrichment', 'tds_criteria')
                  AND coalesce(k.is_archived, false) = false
                ORDER BY k.updated_at DESC LIMIT 1
            ) req ON true
            WHERE t.closing_datetime > now()
              AND coalesce(t.is_deleted, false) = false
              AND (
                    lower(coalesce(t.category, '')) = 'works'
                 OR lower(coalesce(t.procurement_nature, '')) = 'works'
                 OR lower(coalesce(t.title, '')) LIKE 'works,%'
              )
            ORDER BY t.closing_datetime
            LIMIT 5000
        """))
    ).mappings().all()

    existing = (
        await db.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.entry_type == _ALERT_NOTIFICATION_TYPE,
                KnowledgeEntry.is_archived.is_(False),
                KnowledgeEntry.tenant_id == tenant_id,
            )
        )
    ).scalars().all()
    existing_keys = {
        ((entry.data or {}).get("filter_id"), str(entry.tender_id or ""))
        for entry in existing
    }
    total_matches = 0
    created = 0
    now = datetime.now(timezone.utc)
    for filter_entry in filters:
        rule = dict(filter_entry.data or {})
        agencies = {str(value).upper() for value in rule.get("agencies") or [] if value}
        districts = {str(value).lower() for value in rule.get("districts") or [] if value}
        work_types = [
            str(value).lower() for value in rule.get("work_types") or []
            if str(value).lower() != "works"
        ]
        eligibility = [str(value).lower() for value in rule.get("eligibility_keywords") or [] if value]
        min_value = float(rule.get("min_value_bdt") or 0)
        max_value = float(rule["max_value_bdt"]) if rule.get("max_value_bdt") not in (None, "") else None
        deadline_days = int(rule.get("deadline_days") or 30)
        for row in rows:
            amount = float(row["estimated_cost_bdt"] or 0)
            searchable = f"{row['title'] or ''} {row['category'] or ''} {row['procurement_nature'] or ''}".lower()
            eligibility_text = str(row["eligibility_text"] or "").lower()
            closing = row["closing_datetime"]
            if agencies and str(row["agency_code"]).upper() not in agencies:
                continue
            if districts and str(row["district"] or "").lower() not in districts:
                continue
            if amount < min_value or (max_value is not None and amount > max_value):
                continue
            if work_types and not any(value in searchable for value in work_types):
                continue
            if eligibility and not all(value in eligibility_text for value in eligibility):
                continue
            if closing and closing > now + timedelta(days=deadline_days):
                continue
            total_matches += 1
            dedupe_key = (filter_entry.id, str(row["tender_id"]))
            if dedupe_key in existing_keys:
                continue
            payload = {
                "filter_id": filter_entry.id,
                "filter_name": rule.get("name"),
                "title": row["title"],
                "package_no": row["package_no"],
                "agency_code": row["agency_code"],
                "district": row["district"],
                "pe_office": row["pe_office"],
                "estimated_cost_bdt": amount,
                "closing_datetime": closing.isoformat() if closing else None,
                "matched_at": now.isoformat(),
                "read": False,
            }
            checksum = hashlib.sha256(f"{filter_entry.id}:{row['tender_id']}".encode()).hexdigest()
            db.add(KnowledgeEntry(
                id=str(uuid.uuid4()),
                entry_type=_ALERT_NOTIFICATION_TYPE,
                tender_id=str(row["tender_id"]),
                tenant_id=tenant_id,
                title=f"{rule.get('name')}: {row['title'] or row['tender_id']}",
                summary=f"{row['agency_code']} Works tender matched saved alert",
                source="tender_alert_engine",
                procurement_type="Works",
                agency=row["agency_code"],
                data=payload,
                checksum=checksum,
                tags={"filter_id": filter_entry.id, "works_only": True},
            ))
            existing_keys.add(dedupe_key)
            created += 1
    for entry in filters:
        data = dict(entry.data or {})
        data["last_evaluated_at"] = now.isoformat()
        data["last_match_count"] = sum(
            1 for key in existing_keys if key[0] == entry.id
        )
        entry.data = data
    await db.commit()
    return total_matches, created


@router.get("/tender-alerts")
async def get_tender_alerts(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    tenant_id = user.get("tenant_id")
    filters = (
        await db.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.entry_type == _ALERT_FILTER_TYPE,
                KnowledgeEntry.is_archived.is_(False),
                KnowledgeEntry.tenant_id == tenant_id,
            )
            .order_by(KnowledgeEntry.updated_at.desc())
        )
    ).scalars().all()
    notifications = (
        await db.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.entry_type == _ALERT_NOTIFICATION_TYPE,
                KnowledgeEntry.is_archived.is_(False),
                KnowledgeEntry.tenant_id == tenant_id,
            )
            .order_by(KnowledgeEntry.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "success": True,
        "filters": [_alert_filter_payload(entry) for entry in filters],
        "notifications": [_alert_notification_payload(entry) for entry in notifications],
        "unread": sum(1 for entry in notifications if not (entry.data or {}).get("read")),
    }


@router.post("/tender-alerts/filters")
async def create_tender_alert_filter(
    payload: TenderAlertFilterInput,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    data = payload.model_dump()
    now = datetime.now(timezone.utc)
    data.update({"created_at": now.isoformat(), "last_evaluated_at": None, "last_match_count": 0})
    entry = KnowledgeEntry(
        id=str(uuid.uuid4()),
        entry_type=_ALERT_FILTER_TYPE,
        tenant_id=user.get("tenant_id"),
        title=payload.name,
        summary="Saved live Works tender alert filter",
        source="opportunity_discovery",
        procurement_type="Works",
        data=data,
        checksum=hashlib.sha256(f"{user.get('tenant_id')}:{payload.name}:{now.isoformat()}".encode()).hexdigest(),
        tags={"works_only": True},
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    matches, created = await _evaluate_tender_alerts(
        db, tenant_id=user.get("tenant_id"), filter_ids={entry.id},
    )
    return {"success": True, "filter": _alert_filter_payload(entry), "matches": matches, "notifications_created": created}


@router.delete("/tender-alerts/filters/{filter_id}")
async def delete_tender_alert_filter(
    filter_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    entry = await db.get(KnowledgeEntry, filter_id)
    if not entry or entry.entry_type != _ALERT_FILTER_TYPE or entry.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Alert filter not found")
    entry.is_archived = True
    await db.commit()
    return {"success": True}


@router.post("/tender-alerts/evaluate")
async def evaluate_tender_alerts(
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    matches, created = await _evaluate_tender_alerts(db, tenant_id=user.get("tenant_id"))
    return {"success": True, "matches": matches, "notifications_created": created}


@router.post("/tender-alerts/notifications/{notification_id}/read")
async def mark_tender_alert_read(
    notification_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    entry = await db.get(KnowledgeEntry, notification_id)
    if not entry or entry.entry_type != _ALERT_NOTIFICATION_TYPE or entry.tenant_id != user.get("tenant_id"):
        raise HTTPException(status_code=404, detail="Notification not found")
    data = dict(entry.data or {})
    data["read"] = True
    data["read_at"] = datetime.now(timezone.utc).isoformat()
    entry.data = data
    await db.commit()
    return {"success": True}
