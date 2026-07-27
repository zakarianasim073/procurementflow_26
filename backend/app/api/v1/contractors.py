"""Contractor capacity and finance API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_optional_user
from app.db.base import get_async_session
from app.schemas.response_models import ContractorCapacityResponse, ContractorFinanceResponse

router = APIRouter(prefix="/contractors", tags=["contractors"])


async def _contractor_snapshot(db: AsyncSession, identifier: str):
    canonical = await db.execute(text("""
        SELECT
            c.canonical_contractor_id AS id,
            c.display_name AS contractor_name,
            c.total_wins AS total_contracts,
            c.total_award_amount_bdt AS total_amount_bdt,
            c.last_5yr_awarded_amount_bdt,
            c.work_in_hand_bdt,
            c.estimated_turnover_bdt,
            c.tender_capacity_bdt,
            c.total_bids,
            c.win_rate,
            c.reliability_score,
            c.data_confidence_score,
            c.agencies AS agencies_worked,
            c.districts AS districts_worked,
            c.work_type_mix,
            c.is_joint_venture,
            c.jv_member_count,
            CASE WHEN c.total_wins > 0 THEN c.total_award_amount_bdt / c.total_wins ELSE 0 END AS avg_award_bdt,
            'canonical' AS source
        FROM canonical_contractors c
        LEFT JOIN canonical_contractor_aliases a
          ON a.canonical_contractor_id = c.canonical_contractor_id
        WHERE c.canonical_contractor_id = :identifier
           OR c.canonical_name ILIKE :name
           OR c.display_name ILIKE :name
           OR a.alias_name ILIKE :name
           OR a.normalized_alias ILIKE :name
        ORDER BY c.total_award_amount_bdt DESC
        LIMIT 1
    """), {"identifier": identifier, "name": f"%{identifier}%"})
    canonical_row = canonical.mappings().first()
    if canonical_row:
        return canonical_row

    row = await db.execute(text("""
        SELECT c.id, c.contractor_name, c.total_contracts, c.total_amount_bdt,
               c.agencies_worked, c.districts_worked, c.avg_npp,
               cd.avg_award_bdt, cd.agencies_worked AS agencies_count,
               cd.districts_worked AS districts_count, cd.win_rate,
               cd.avg_discount_pct, cd.health_score, cd.completion_rate,
               cd.on_time_rate, cd.avg_delay_days,
               NULL::double precision AS last_5yr_awarded_amount_bdt,
               NULL::double precision AS work_in_hand_bdt,
               NULL::double precision AS estimated_turnover_bdt,
               NULL::double precision AS tender_capacity_bdt,
               NULL::integer AS total_bids,
               NULL::double precision AS reliability_score,
               NULL::double precision AS data_confidence_score,
               '{}'::jsonb AS work_type_mix,
               false AS is_joint_venture,
               0 AS jv_member_count,
               'legacy' AS source
        FROM contractors c
        LEFT JOIN contractor_dna cd ON cd.contractor_id = c.id
        WHERE c.id = :identifier OR c.contractor_name ILIKE :name
        ORDER BY c.total_amount_bdt DESC
        LIMIT 1
    """), {"identifier": identifier, "name": f"%{identifier}%"})
    return row.mappings().first()


@router.get("/{identifier}/capacity", response_model=ContractorCapacityResponse)
async def contractor_capacity(
    identifier: str,
    tender_value_bdt: float = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    row = await _contractor_snapshot(db, identifier)
    if not row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    avg_award = float(row.get("avg_award_bdt") or 0)
    total_amount = float(row.get("total_amount_bdt") or 0)
    capacity_basis = float(row.get("tender_capacity_bdt") or 0) or max(avg_award * 3, total_amount * 0.20)
    utilization = (tender_value_bdt / capacity_basis) if capacity_basis and tender_value_bdt else 0.0
    return {
        "success": True,
        "contractor": row["contractor_name"],
        "canonical_contractor_id": row["id"],
        "total_contracts": row["total_contracts"] or 0,
        "total_amount_bdt": total_amount,
        "last_5yr_awarded_amount_bdt": float(row.get("last_5yr_awarded_amount_bdt") or 0),
        "work_in_hand_bdt": float(row.get("work_in_hand_bdt") or 0),
        "estimated_turnover_bdt": float(row.get("estimated_turnover_bdt") or 0),
        "avg_award_bdt": avg_award,
        "tender_capacity_bdt": capacity_basis,
        "tender_value_bdt": tender_value_bdt,
        "utilization_ratio": utilization,
        "capacity_status": "overloaded" if utilization > 1 else "tight" if utilization > 0.75 else "available",
        "agencies_worked": row.get("agencies_worked") or [],
        "districts_worked": row.get("districts_worked") or [],
        "work_type_mix": row.get("work_type_mix") or {},
        "is_joint_venture": bool(row.get("is_joint_venture") or False),
        "jv_member_count": row.get("jv_member_count") or 0,
        "data_confidence_score": float(row.get("data_confidence_score") or 0),
        "source": row.get("source"),
    }


@router.get("/{identifier}/finance", response_model=ContractorFinanceResponse)
async def contractor_finance(
    identifier: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    row = await _contractor_snapshot(db, identifier)
    if not row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    total_amount = float(row.get("total_amount_bdt") or 0)
    avg_award = float(row.get("avg_award_bdt") or 0)
    return {
        "success": True,
        "contractor": row["contractor_name"],
        "canonical_contractor_id": row["id"],
        "total_contracts": row["total_contracts"] or 0,
        "total_amount_bdt": total_amount,
        "last_5yr_awarded_amount_bdt": float(row.get("last_5yr_awarded_amount_bdt") or 0),
        "work_in_hand_bdt": float(row.get("work_in_hand_bdt") or 0),
        "estimated_turnover_bdt": float(row.get("estimated_turnover_bdt") or 0),
        "tender_capacity_bdt": float(row.get("tender_capacity_bdt") or 0),
        "avg_award_bdt": avg_award,
        "avg_npp": float(row.get("avg_npp") or 0),
        "avg_discount_pct": float(row.get("avg_discount_pct") or 0),
        "win_rate": float(row.get("win_rate") or 0),
        "total_bids": row.get("total_bids") or 0,
        "health_score": float(row.get("health_score") or row.get("reliability_score") or 0),
        "reliability_score": float(row.get("reliability_score") or 0),
        "data_confidence_score": float(row.get("data_confidence_score") or 0),
        "completion_rate": float(row.get("completion_rate") or 0),
        "on_time_rate": float(row.get("on_time_rate") or 0),
        "avg_delay_days": float(row.get("avg_delay_days") or 0),
        "estimated_liquidity_band_bdt": {
            "low": round(avg_award * 0.10, 2),
            "high": round(max(avg_award * 0.25, total_amount * 0.03), 2),
        },
        "work_type_mix": row.get("work_type_mix") or {},
        "is_joint_venture": bool(row.get("is_joint_venture") or False),
        "jv_member_count": row.get("jv_member_count") or 0,
        "source": row.get("source"),
    }
