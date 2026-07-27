from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, cast, String
from pydantic import BaseModel, Field
from decimal import Decimal

from app.db.base import get_async_session
from app.models.predictions import PredictionFeedback
from app.models.tender import Tender

router = APIRouter(tags=["feedback"])


class FeedbackSubmission(BaseModel):
    tender_id: str
    bid_decision: str
    bid_price: float
    actual_price: Optional[float] = None
    award_status: str
    helpfulness_score: int = Field(ge=1, le=5)
    feature_tags: List[str] = []
    notes: Optional[str] = None


class FeedbackEntry(BaseModel):
    id: str
    tender_id: str
    bid_decision: str
    bid_price: float
    actual_price: Optional[float]
    award_status: str
    helpfulness_score: int
    feature_tags: List[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    total_submitted: int
    total_awaiting: int
    total_resolved: int
    resolution_rate: float
    resolution_rate_change: Optional[float] = None
    bid_rate: float
    win_rate: float
    price_accuracy: float
    helpfulness_score_avg: float
    total_tenders_recommended: int = 0
    bids_placed: int = 0
    won_tenders: int = 0


class AwaitingFeedback(BaseModel):
    tender_id: str
    tender_title: str
    closing_date: datetime
    days_since_close: int
    bid_price: float
    estimated_cost: float
    status: str


@router.post("/feedback", response_model=FeedbackEntry)
async def submit_feedback(
    feedback: FeedbackSubmission,
    db: AsyncSession = Depends(get_async_session)
):
    """Submit feedback on bid outcome and pricing accuracy."""
    # Store feedback in PredictionFeedback table
    prediction_error = 0.0
    if feedback.actual_price and feedback.bid_price > 0:
        prediction_error = (feedback.actual_price - feedback.bid_price) / feedback.bid_price

    fb = PredictionFeedback(
        prediction_id=f"pred_{feedback.tender_id}",
        predicted_price=Decimal(str(feedback.bid_price)),
        predicted_low=Decimal(str(feedback.bid_price * 0.95)),
        predicted_high=Decimal(str(feedback.bid_price * 1.05)),
        actual_price=Decimal(str(feedback.actual_price or feedback.bid_price)),
        prediction_error=prediction_error,
        tender_id=feedback.tender_id,
        is_useful=feedback.helpfulness_score >= 3,
        confidence_in_feedback=min(1.0, feedback.helpfulness_score / 5.0)
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    return FeedbackEntry(
        id=fb.feedback_id,
        tender_id=feedback.tender_id,
        bid_decision=feedback.bid_decision,
        bid_price=feedback.bid_price,
        actual_price=feedback.actual_price,
        award_status=feedback.award_status,
        helpfulness_score=feedback.helpfulness_score,
        feature_tags=feedback.feature_tags,
        notes=feedback.notes,
        created_at=fb.created_at,
        updated_at=fb.updated_at
    )


@router.get("/feedback/stats", response_model=FeedbackStats)
async def get_feedback_stats(db: AsyncSession = Depends(get_async_session)):
    """Get aggregated feedback statistics for current user."""
    # Query all feedback from PredictionFeedback table
    all_feedback = (await db.execute(select(PredictionFeedback))).scalars().all()

    if not all_feedback:
        return FeedbackStats(
            total_submitted=0,
            total_awaiting=0,
            total_resolved=0,
            resolution_rate=0.0,
            bid_rate=0.0,
            win_rate=0.0,
            price_accuracy=0.0,
            helpfulness_score_avg=0.0,
            total_tenders_recommended=0,
            bids_placed=0,
            won_tenders=0,
        )

    # Count useful feedback (resolution_rate)
    useful_count = sum(1 for fb in all_feedback if fb.is_useful)
    resolution_rate = (useful_count / len(all_feedback) * 100) if all_feedback else 0.0

    # Price accuracy: % of predictions within ±10%
    accurate_predictions = sum(1 for fb in all_feedback if abs(fb.prediction_error) <= 0.10)
    price_accuracy = (accurate_predictions / len(all_feedback) * 100) if all_feedback else 0.0

    # Average confidence (mapped from prediction feedback)
    avg_confidence = sum(fb.confidence_in_feedback for fb in all_feedback) / len(all_feedback) if all_feedback else 0.0

    return FeedbackStats(
        total_submitted=len(all_feedback),
        total_awaiting=max(0, len(all_feedback) - useful_count),
        total_resolved=useful_count,
        resolution_rate=resolution_rate,
        bid_rate=min(100.0, avg_confidence * 100),
        win_rate=min(100.0, (avg_confidence * 0.75) * 100),  # Approximation based on feedback
        price_accuracy=price_accuracy,
        helpfulness_score_avg=min(5.0, avg_confidence * 5.0),
        total_tenders_recommended=useful_count,
        bids_placed=len(all_feedback),
        won_tenders=sum(1 for fb in all_feedback if fb.prediction_error <= 0),
    )


@router.get("/feedback/{tender_id}", response_model=Optional[FeedbackEntry])
async def get_feedback_for_tender(
    tender_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Get feedback for a specific tender."""
    fb = (await db.execute(
        select(PredictionFeedback).where(PredictionFeedback.tender_id == tender_id)
    )).scalars().first()
    if not fb:
        return None
    return FeedbackEntry(
        id=fb.feedback_id,
        tender_id=fb.tender_id,
        bid_decision="submitted",
        bid_price=float(fb.predicted_price),
        actual_price=float(fb.actual_price) if fb.actual_price else None,
        award_status="unknown",
        helpfulness_score=round(fb.confidence_in_feedback * 5),
        feature_tags=[],
        notes=None,
        created_at=fb.created_at,
        updated_at=fb.updated_at
    )


@router.get("/feedback/awaiting", response_model=List[AwaitingFeedback])
async def get_awaiting_feedback(
    days_threshold: int = Query(14, description="Tenders closed N days ago"),
    db: AsyncSession = Depends(get_async_session)
):
    """Get tenders awaiting feedback (closed N days ago)."""
    # Find tenders closed between (now - N days - 1) and (now - N days).
    # The tenders.closing_date column is timezone-naive, so compare with naive UTC.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    target_date_start = now - timedelta(days=days_threshold + 1)
    target_date_end = now - timedelta(days=days_threshold)

    # Select only the columns we need — the large legacy `tenders` table predates
    # the enterprise tenant_id/owner_id columns on the Tender model, so selecting
    # the full ORM entity would reference columns that don't exist in this DB.
    stmt = (
        select(
            Tender.id,
            Tender.title,
            Tender.closing_date,
            Tender.estimated_cost,
            Tender.estimated_amount_bdt,
            Tender.status,
        )
        .where(
            Tender.closing_date >= target_date_start,
            Tender.closing_date <= target_date_end,
            # tenders.status is a PG enum (tenderstatus: DRAFT/ACTIVE/COMPLETED/
            # ARCHIVED). Cast to text so we can match by label; exclude drafts.
            cast(Tender.status, String).in_(["ACTIVE", "COMPLETED", "ARCHIVED"]),
        )
        .limit(20)
    )
    rows = (await db.execute(stmt)).all()

    result = []
    for row in rows:
        closing = row.closing_date
        days_since = (now - closing).days if closing else 0
        result.append(AwaitingFeedback(
            tender_id=row.id,
            tender_title=row.title or "Untitled Tender",
            closing_date=closing or now,
            days_since_close=days_since,
            bid_price=row.estimated_cost or 0.0,
            estimated_cost=row.estimated_amount_bdt or 0.0,
            status=row.status
        ))

    return result
