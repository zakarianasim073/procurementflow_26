"""Canonical identity and normalization quality endpoints."""

import json
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.db.base import get_async_session
from app.schemas.response_models import (
    AdminActionResult,
    CanonicalStatusResponse,
    RepairQueueResponse,
    RepairQueueSummaryResponse,
    RepairResolveResponse,
    SuccessWithData,
)

router = APIRouter(prefix="/canonical", tags=["canonical"])


class RepairResolution(BaseModel):
    status: str = "resolved"
    suggested_action: str | None = None
    evidence: dict[str, Any] | None = None


@router.get("/status", response_model=CanonicalStatusResponse)
async def canonical_status(
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_role("owner", "admin")),
):
    """Return canonical rebuild and data-quality status for owner/admin review."""
    counts = (await db.execute(text("""
        SELECT
            (SELECT count(*) FROM canonical_tenders) AS tenders,
            (SELECT count(*) FROM canonical_contracts) AS contracts,
            (SELECT count(*) FROM canonical_contractors) AS contractors,
            (SELECT count(*) FROM canonical_contractor_aliases) AS aliases,
            (SELECT count(*) FROM canonical_contractor_jv_members) AS jv_links,
            (SELECT count(*) FROM amount_normalization_audit) AS amount_audit_rows
    """))).mappings().one()

    amount_quality = (await db.execute(text("""
        SELECT
            count(*) FILTER (WHERE amount_confidence >= 0.7) AS trusted_amounts,
            count(*) FILTER (WHERE amount_confidence > 0 AND amount_confidence < 0.7) AS low_confidence_amounts,
            count(*) FILTER (WHERE amount_confidence = 0) AS missing_or_rejected_amounts,
            count(*) FILTER (WHERE amount_warning IS NOT NULL) AS warning_rows,
            count(*) FILTER (WHERE amount_warning = 'suspicious_huge_amount_excluded_from_capacity') AS suspicious_huge_amounts,
            count(*) FILTER (WHERE amount_warning = 'suspicious_tiny_amount_kept_unscaled') AS suspicious_tiny_amounts,
            coalesce(round(avg(amount_confidence)::numeric, 4), 0) AS avg_amount_confidence
        FROM canonical_contracts
    """))).mappings().one()

    contractor_quality = (await db.execute(text("""
        SELECT
            count(*) FILTER (WHERE total_award_amount_bdt > 0) AS contractors_with_amounts,
            count(*) FILTER (WHERE tender_capacity_bdt > 0) AS contractors_with_capacity,
            count(*) FILTER (WHERE is_joint_venture) AS joint_venture_contractors,
            coalesce(round(avg(data_confidence_score)::numeric, 4), 0) AS avg_data_confidence,
            max(rebuilt_at) AS last_rebuilt_at
        FROM canonical_contractors
    """))).mappings().one()

    top_capacity = (await db.execute(text("""
        SELECT
            canonical_contractor_id,
            display_name,
            total_wins,
            total_award_amount_bdt,
            last_5yr_awarded_amount_bdt,
            work_in_hand_bdt,
            estimated_turnover_bdt,
            tender_capacity_bdt,
            data_confidence_score
        FROM canonical_contractors
        WHERE tender_capacity_bdt > 0
        ORDER BY tender_capacity_bdt DESC
        LIMIT 10
    """))).mappings().all()

    return {
        "success": True,
        "requested_by": {
            "user_id": user.get("id"),
            "tenant_id": user.get("tenant_id"),
            "role": user.get("role"),
        },
        "tables": dict(counts),
        "amount_quality": dict(amount_quality),
        "contractor_quality": dict(contractor_quality),
        "top_capacity_contractors": [dict(row) for row in top_capacity],
    }


@router.get("/repair-queue/summary", response_model=RepairQueueSummaryResponse)
async def repair_queue_summary(
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_role("owner", "admin")),
):
    rows = (await db.execute(text("""
        SELECT issue_type, status, severity, count(*) AS count
        FROM canonical_identity_repair_queue
        GROUP BY issue_type, status, severity
        ORDER BY count DESC
    """))).mappings().all()
    return {"success": True, "summary": [dict(row) for row in rows]}


@router.get("/repair-queue", response_model=RepairQueueResponse)
async def list_repair_queue(
    status: str = Query("open"),
    issue_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_role("owner", "admin")),
):
    where = ["status = :status"]
    params: dict[str, Any] = {"status": status, "limit": limit, "offset": offset}
    if issue_type:
        where.append("issue_type = :issue_type")
        params["issue_type"] = issue_type
    # sql-ok: WHERE fragments from code constants; values bound
    query = f"""
        SELECT repair_id, entity_type, entity_key, source_table, source_id,
               issue_type, confidence, severity, status, suggested_action,
               evidence, created_at, updated_at
        FROM canonical_identity_repair_queue
        WHERE {' AND '.join(where)}
        ORDER BY severity DESC, confidence ASC, created_at DESC
        LIMIT :limit OFFSET :offset
    """
    rows = (await db.execute(text(query), params)).mappings().all()
    total = (await db.execute(
        # sql-ok: WHERE fragments from code constants; values bound
        text(f"SELECT count(*) FROM canonical_identity_repair_queue WHERE {' AND '.join(where)}"),
        {k: v for k, v in params.items() if k not in {"limit", "offset"}},
    )).scalar()
    return {"success": True, "total": total, "limit": limit, "offset": offset, "records": [dict(row) for row in rows]}


@router.get("/package-no/quality", response_model=SuccessWithData)
async def package_no_quality(
    user: dict = Depends(require_role("owner", "admin")),
):
    """T-029: Current data-quality metrics for award→tender FK resolution.

    Shows how many award_records_v2 rows still have a broken (NULL)
    procurement_tender_id and what fraction have been resolved via
    normalized_package_no matching.
    """
    from app.services.package_no_repair_service import PackageNoRepairService
    metrics = PackageNoRepairService.get_quality_metrics()
    return {"success": True, **metrics}


@router.post("/package-no/repair", response_model=AdminActionResult)
async def trigger_package_no_repair(
    user: dict = Depends(require_role("owner", "admin")),
):
    """T-029: Manually trigger a synchronous package-number repair pass.

    Prefer the nightly Celery Beat task (`repair_package_nos`) for production.
    This endpoint exists for admin/ops use during initial data migration.
    """
    from app.services.package_no_repair_service import PackageNoRepairService
    result = PackageNoRepairService.repair()
    return {"success": True, **result}


@router.post("/repair-queue/{repair_id}/resolve", response_model=RepairResolveResponse)
async def resolve_repair_item(
    repair_id: str,
    payload: RepairResolution,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_role("owner", "admin")),
):
    result = await db.execute(text("""
        UPDATE canonical_identity_repair_queue
        SET status = :status,
            suggested_action = COALESCE(:suggested_action, suggested_action),
            evidence = CASE WHEN :evidence IS NULL THEN evidence ELSE evidence || CAST(:evidence AS jsonb) END,
            updated_at = now(),
            resolved_at = CASE WHEN :status IN ('resolved','ignored') THEN now() ELSE resolved_at END
        WHERE repair_id = :repair_id
        RETURNING repair_id, status, updated_at, resolved_at
    """), {
        "repair_id": repair_id,
        "status": payload.status,
        "suggested_action": payload.suggested_action,
        "evidence": None if payload.evidence is None else json.dumps(payload.evidence, default=str),
    })
    row = result.mappings().first()
    if not row:
        return {"success": False, "error": "repair item not found"}
    await db.commit()
    return {"success": True, "record": dict(row)}
