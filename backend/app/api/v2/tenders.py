"""Phase 2: Tender Management Endpoints — uses actual Tender model schema"""

from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import String, cast, select, desc, or_
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_async_session
from app.core.security import get_current_user
from app.models.tender import Tender

router = APIRouter(prefix="/tenders", tags=["tenders"])


class TenderResponse(BaseModel):
    id: str
    tender_id: str
    package_no: Optional[str] = None
    title: Optional[str] = None
    procuring_entity: Optional[str] = None
    district: Optional[str] = None
    division: Optional[str] = None
    estimated_cost: Optional[float] = None
    closing_date: Optional[datetime] = None
    opening_date: Optional[datetime] = None
    status: Optional[str] = None
    zone: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenderUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    estimated_cost: Optional[float] = None
    closing_date: Optional[datetime] = None


@router.get("", response_model=List[TenderResponse])
async def list_tenders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    agency: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List tenders with optional search, status filter, and pagination."""
    try:
        query = select(Tender)

        if q:
            query = query.where(
                or_(
                    Tender.title.ilike(f"%{q}%"),
                    Tender.tender_id.ilike(f"%{q}%"),
                    Tender.procuring_entity.ilike(f"%{q}%"),
                )
            )
        if status:
            query = query.where(cast(Tender.status, String) == status)
        if agency:
            query = query.where(Tender.procuring_entity.ilike(f"%{agency}%"))

        query = query.order_by(desc(Tender.closing_date)).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender(
    tender_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get tender by row ID or tender_id string."""
    try:
        result = await db.execute(
            select(Tender).where(
                or_(Tender.id == tender_id, Tender.tender_id == tender_id)
            )
        )
        tender = result.scalar_one_or_none()
        if not tender:
            raise HTTPException(status_code=404, detail="Tender not found")
        return tender
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{tender_id}", response_model=TenderResponse)
async def update_tender(
    tender_id: str,
    tender_update: TenderUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update allowed tender fields."""
    try:
        result = await db.execute(
            select(Tender).where(
                or_(Tender.id == tender_id, Tender.tender_id == tender_id)
            )
        )
        tender = result.scalar_one_or_none()
        if not tender:
            raise HTTPException(status_code=404, detail="Tender not found")

        for field, value in tender_update.model_dump(exclude_unset=True).items():
            setattr(tender, field, value)

        await db.commit()
        await db.refresh(tender)
        return tender
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
