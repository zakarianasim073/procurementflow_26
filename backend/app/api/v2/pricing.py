from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

from app.db.base import get_async_session
from app.services.bid_predictor import bid_predictor

router = APIRouter(tags=["pricing"])


class PricingPrediction(BaseModel):
    bid_price: float
    discount_percent: float
    win_probability: float
    confidence_band_low: float
    confidence_band_high: float
    expected_value: float
    reasoning: str
    evidence: List[dict]
    comparable_bids: List[dict]
    recommendation: str


class PricingHistoryEntry(BaseModel):
    id: str
    tender_id: str
    bid_price: float
    estimated_cost: float
    bidder_count: int
    discount_percent: float
    win_probability: float
    agency: str
    zone: str
    created_at: str


class PricingStrategy(BaseModel):
    id: str
    tender_id: str
    name: str
    discount_percent: float
    bid_price: float
    rationale: str
    created_at: str
    updated_at: str


class SaveStrategyRequest(BaseModel):
    name: str
    discount_percent: float
    bid_price: float
    rationale: str


# In-memory store for pricing strategies (persists per server process)
_pricing_strategies: Dict[str, Dict[str, Any]] = {}


# Track pricing history in-memory (persists per server process)
_pricing_history: Dict[str, List[Dict[str, Any]]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _history_key(tender_id: str, agency: str, zone: str) -> str:
    return f"{tender_id}:{agency or 'ALL'}:{zone or 'ALL'}"


@router.get("/tender/{tender_id}/pricing-lab/prediction", response_model=PricingPrediction)
async def get_pricing_prediction(
    tender_id: str,
    bid_price: float = Query(...),
    estimated_cost: float = Query(...),
    bidder_count: int = Query(...),
    agency: Optional[str] = None,
    zone: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
):
    """Get AI win probability prediction using real discount patterns from discount_patterns table."""
    pred = await bid_predictor.predict(
        tender_id=tender_id,
        agency=agency or "",
        estimate=estimated_cost,
        work_type="Civil Works",
        num_bidders=bidder_count,
        db=db,
    )

    discount = ((estimated_cost - bid_price) / estimated_cost) * 100
    expected_discount = pred["predicted"]["expected_discount_pct"]

    discount_gap = abs(discount - expected_discount)
    if discount_gap < 1.0:
        win_prob = 75 + (bidder_count < 5) * 10
    elif discount_gap < 3.0:
        win_prob = 55
    else:
        win_prob = max(10, 40 - discount_gap * 5)

    confidence = 0.04 if pred.get("sample_size", 0) > 50 else 0.08 if pred.get("sample_size", 0) > 10 else 0.12

    margin = (bid_price - estimated_cost * 0.85) / bid_price * 100
    expected_value = margin * win_prob / 100

    comp_result = await db.execute(text("""
        SELECT tender_id, agency_code, amount_bdt, npp
        FROM award_records_v2
        WHERE agency_code = :agency AND npp IS NOT NULL AND npp BETWEEN :low AND :high
        ORDER BY award_date DESC LIMIT 5
    """), {"agency": agency or "LGED", "low": expected_discount - 3, "high": expected_discount + 3})
    comparable_bids = []
    for row in comp_result.mappings().all():
        comparable_bids.append({
            "tender_id": row["tender_id"] or "UNKNOWN",
            "bidder_count": bidder_count,
            "winning_bid": float(row["amount_bdt"] or 0),
            "your_discount": round(float(row["npp"] or 0), 2),
        })

    sample_size = pred.get("sample_size", 0)

    return PricingPrediction(
        bid_price=bid_price,
        discount_percent=discount,
        win_probability=win_prob,
        confidence_band_low=max(10, win_prob - (win_prob * confidence)),
        confidence_band_high=min(95, win_prob + (win_prob * confidence)),
        expected_value=expected_value,
        reasoning=f"Agency {agency or 'Unknown'}: expected discount {expected_discount:.1f}% (from {sample_size} samples). "
                  f"Your discount {discount:.1f}% → {win_prob:.0f}% win probability.",
        evidence=[
            {"source": "discount_patterns", "agency": agency or "Unknown", "sample_size": sample_size,
             "expected_discount": expected_discount, "your_discount": round(discount, 2)},
        ],
        comparable_bids=comparable_bids if comparable_bids else [
            {"tender_id": "N/A", "bidder_count": bidder_count,
             "winning_bid": round(estimated_cost * (1 - expected_discount / 100), 2),
             "your_discount": round(discount, 2)},
        ],
        recommendation="COMPETITIVE" if win_prob > 60 else "RISKY" if win_prob < 40 else "BALANCED"
    )


@router.get("/tender/{tender_id}/pricing-lab/history", response_model=List[PricingHistoryEntry])
async def get_pricing_history(
    tender_id: str,
    agency: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    """Return historical bid/pricing data from award_records_v2 for comparable analysis."""
    key = _history_key(tender_id, agency, zone)
    if key in _pricing_history:
        entries = _pricing_history[key]
    else:
        rows = await db.execute(text("""
            SELECT tender_id, agency_code, amount_bdt, npp, award_date, zone
            FROM award_records_v2
            WHERE agency_code = :agency AND npp IS NOT NULL
            ORDER BY award_date DESC LIMIT :limit
        """), {"agency": agency or "LGED", "limit": limit})
        entries = []
        for row in rows.mappings().all():
            npp = float(row["npp"] or 0)
            amount = float(row["amount_bdt"] or 0)
            entries.append({
                "id": str(uuid.uuid4()),
                "tender_id": row["tender_id"] or tender_id,
                "bid_price": round(amount * (1 - npp / 100), 2),
                "estimated_cost": round(amount / (1 - npp / 100), 2) if npp < 100 else amount,
                "bidder_count": 0,
                "discount_percent": round(npp, 2),
                "win_probability": 0,
                "agency": row["agency_code"] or agency or "Unknown",
                "zone": row["zone"] or zone or "Unknown",
                "created_at": row["award_date"] or _now_iso(),
            })
        _pricing_history[key] = entries

    return entries[:limit]


@router.post("/tender/{tender_id}/pricing-strategy", response_model=PricingStrategy)
async def save_pricing_strategy(
    tender_id: str,
    req: SaveStrategyRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Save a named pricing strategy for a tender."""
    strategy_id = str(uuid.uuid4())
    now = _now_iso()
    _pricing_strategies[strategy_id] = {
        "id": strategy_id,
        "tender_id": tender_id,
        "name": req.name,
        "discount_percent": req.discount_percent,
        "bid_price": req.bid_price,
        "rationale": req.rationale,
        "created_at": now,
        "updated_at": now,
    }
    return PricingStrategy(**_pricing_strategies[strategy_id])


@router.get("/tender/{tender_id}/pricing-strategy/{strategy_id}", response_model=PricingStrategy)
async def get_pricing_strategy(
    tender_id: str,
    strategy_id: str,
):
    """Retrieve a saved pricing strategy by ID."""
    if strategy_id not in _pricing_strategies:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Strategy not found")
    return PricingStrategy(**_pricing_strategies[strategy_id])
