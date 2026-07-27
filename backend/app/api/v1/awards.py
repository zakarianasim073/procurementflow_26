"""Award Intelligence API routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, text
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.base import get_async_session
from app.models.award import Award
from app.schemas.award import AwardRecordCreate as AwardCreate, AwardRecordRead as AwardRead
from app.core.security import get_optional_user, get_current_user
from app.schemas.response_models import SimpleSuccessResponse
from pydantic import BaseModel as _PydanticBaseModel
from typing import List as _List

class AwardStatsResponse(_PydanticBaseModel):
    total_awards: int = 0
    total_awarded_amount: float = 0
    avg_discount_pct: float = 0
    top_entities: _List[dict] = []
    top_contractors: _List[dict] = []

router = APIRouter(prefix="/awards", tags=["awards"])


@router.post("/", response_model=AwardRead)
async def create_award(
    award: AwardCreate,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    """Create a new award record"""
    db_award = Award(**award.model_dump())
    db.add(db_award)
    await db.commit()
    await db.refresh(db_award)
    return db_award


@router.get("/", response_model=List[AwardRead])
async def list_awards(
    procuring_entity: Optional[str] = Query(None),
    contractor_name: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    work_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """List award records with filters"""
    stmt = select(Award)
    
    if procuring_entity:
        stmt = stmt.where(Award.procuring_entity.ilike(f"%{procuring_entity}%"))
    if contractor_name:
        stmt = stmt.where(Award.contractor_name.ilike(f"%{contractor_name}%"))
    if district:
        stmt = stmt.where(Award.district.ilike(f"%{district}%"))
    if work_type:
        stmt = stmt.where(Award.work_type.ilike(f"%{work_type}%"))
    if date_from:
        stmt = stmt.where(Award.award_date >= date_from)
    if date_to:
        stmt = stmt.where(Award.award_date <= date_to)
    
    stmt = stmt.order_by(desc(Award.award_date)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/stats", response_model=AwardStatsResponse)
async def get_award_stats(
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """Get award statistics"""
    amount_expr = "COALESCE(amount_bdt, award_amount, 0)"
    summary = (
        await db.execute(
            text(
                f"""
                SELECT count(*)::bigint AS total,
                       COALESCE(sum({amount_expr}), 0)::double precision AS total_amount
                FROM awards
                """
            )
        )
    ).mappings().one()
    avg_discount = await db.scalar(
        text(
            """
            SELECT COALESCE(avg(discount_pct), 0)::double precision
            FROM award_records_v2
            WHERE discount_pct IS NOT NULL
            """
        )
    )

    top_entities = (
        await db.execute(
            text(
                f"""
                SELECT COALESCE(NULLIF(agency, ''), 'Unknown') AS name,
                       count(*)::bigint AS count,
                       COALESCE(sum({amount_expr}), 0)::double precision AS total_amount
                FROM awards
                GROUP BY COALESCE(NULLIF(agency, ''), 'Unknown')
                ORDER BY total_amount DESC
                LIMIT 10
                """
            )
        )
    ).mappings().all()

    top_contractors = (
        await db.execute(
            text(
                f"""
                SELECT COALESCE(NULLIF(contractor_name, ''), 'Unknown') AS name,
                       count(*)::bigint AS count,
                       COALESCE(sum({amount_expr}), 0)::double precision AS total_amount
                FROM awards
                GROUP BY COALESCE(NULLIF(contractor_name, ''), 'Unknown')
                ORDER BY total_amount DESC
                LIMIT 10
                """
            )
        )
    ).mappings().all()
    
    return {
        "total_awards": int(summary["total"] or 0),
        "total_awarded_amount": float(summary["total_amount"] or 0),
        "avg_discount_pct": float(avg_discount) if avg_discount else 0,
        "top_entities": [
            {"name": r["name"], "count": int(r["count"]), "total_amount": float(r["total_amount"] or 0)}
            for r in top_entities
        ],
        "top_contractors": [
            {"name": r["name"], "count": int(r["count"]), "total_amount": float(r["total_amount"] or 0)}
            for r in top_contractors
        ],
    }


@router.get("/{award_id}", response_model=AwardRead)
async def get_award(
    award_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """Get award by ID"""
    stmt = select(Award).where(Award.id == award_id)
    result = await db.execute(stmt)
    award = result.scalar_one_or_none()
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    return award
