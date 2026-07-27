"""Pricing API routes — fast SOR-backed estimates."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.security import get_optional_user
from app.schemas.response_models import PricingEstimateResponse
from app.sor.sor_service import sor_service

router = APIRouter(prefix="/pricing", tags=["pricing"])


class PricingItem(BaseModel):
    code: str = ""
    description: str = ""
    unit: str = ""
    quantity: float = 0.0
    agency: Optional[str] = None
    zone: Optional[str] = None


class PricingEstimateRequest(BaseModel):
    items: List[PricingItem] = Field(default_factory=list)
    agency: str = "BWDB"
    zone: str = "A"


def _estimate_items(items: List[PricingItem], agency: str, zone: str) -> Dict[str, Any]:
    if not sor_service._loaded:
        sor_service.load_all(prefer_db=False)

    rows = []
    total = 0.0
    matched = 0
    for item in items:
        item_agency = item.agency or agency
        item_zone = item.zone or zone
        rate, record = sor_service.find_rate(item.code, item.description, item_agency, item_zone)
        confidence = 1.0 if record and item.code and record.code.lower() == item.code.lower() else 0.0
        if record is None and item.description:
            rate, record, confidence = sor_service.find_rate_by_description(
                item.description, item_agency, item_zone, unit=item.unit, threshold=0.42
            )
        amount = float(item.quantity or 0) * float(rate or 0)
        if record:
            matched += 1
        total += amount
        rows.append({
            "code": item.code,
            "description": item.description,
            "unit": item.unit,
            "quantity": item.quantity,
            "agency": record.agency if record else item_agency,
            "zone": item_zone,
            "rate": rate,
            "amount": amount,
            "sor_code": record.code if record else None,
            "sor_description": record.description if record else None,
            "confidence": confidence,
            "matched": record is not None,
        })
    return {
        "success": True,
        "items": rows,
        "total_items": len(rows),
        "matched_items": matched,
        "unmatched_items": len(rows) - matched,
        "estimated_total": total,
        "source": "sor_service_csv_indexed",
    }


@router.post("/estimate", response_model=PricingEstimateResponse)
async def estimate_pricing(req: PricingEstimateRequest, user: dict = Depends(get_optional_user)):
    return _estimate_items(req.items, req.agency, req.zone)


@router.get("/estimate", response_model=PricingEstimateResponse)
async def estimate_single_item(
    code: str = Query(""),
    description: str = Query(""),
    unit: str = Query(""),
    quantity: float = Query(1.0),
    agency: str = Query("BWDB", pattern="^(BWDB|PWD|LGED)$"),
    zone: str = Query("A", pattern="^(A|B|C|D)$"),
    user: dict = Depends(get_optional_user),
):
    return _estimate_items(
        [PricingItem(code=code, description=description, unit=unit, quantity=quantity, agency=agency, zone=zone)],
        agency,
        zone,
    )
