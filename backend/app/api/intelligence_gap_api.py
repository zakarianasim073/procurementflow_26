"""
Intelligence Gap-Filler API — contractor sub-routes the frontend_v2 calls
that no other router serves.

Existing routers handle: /executive/*, /search/tenders, /agencies,
/opening-reports, /agent-results/recent, /tender-radar, /tenders/{id} (brain_router).

This file serves ONLY: /contractors/{id}/* sub-routes
(5 endpoints, all behind auth like the rest of the API).

Tables used:
  - award_records_v2: id (uuid), tender_id, amount_bdt, contractor_name,
    contractor_id, agency_code, package_no, award_date, category
  - canonical_tenders: tender_id, tender_name, agency_code, estimated_cost_bdt, status

Mounted at /api in main.py.
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_async_session
from app.schemas.response_models import (
    ContractorExperienceItem,
    ContractorAwardsPage,
    EligibilityRule,
    ContractorRiskResponse,
    ContractorOpportunityItem,
    ContractorExperienceCategory,
    ContractorExperienceResponse,
    ContractorEligibilityResponse,
    ContractorRiskProfileResponse,
    RiskFlag,
)

router = APIRouter(tags=["intelligence-gap"])


def _dec(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _dec(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_dec(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# 1. Contractor Experience
# ---------------------------------------------------------------------------

@router.get("/contractors/{company_id}/experience", response_model=ContractorExperienceResponse)
async def contractor_experience(
    company_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    r = await db.execute(text("""
        SELECT 'Works' AS category, COUNT(*) AS cnt,
               AVG(amount_bdt) AS avg_val, MAX(amount_bdt) AS max_val
        FROM award_records_v2
        WHERE contractor_name ILIKE :cid OR canonical_contractor_id::text = :cid2
        ORDER BY cnt DESC
    """), {"cid": f"%{company_id}%", "cid2": company_id})
    
    categories = [
        ContractorExperienceCategory(
            category=row["category"] or "Unknown",
            projects_count=row["cnt"],
            avg_value=_dec(row["avg_val"] or 0),
            largest_value=_dec(row["max_val"] or 0),
            years_active=1,
            trend="stable",
        )
        for row in r.mappings().all()
    ]
    
    total_years = len(categories) if categories else 0
    return ContractorExperienceResponse(
        total_years=total_years,
        by_category=categories,
    )


# ---------------------------------------------------------------------------
# 2. Contractor Awards
# ---------------------------------------------------------------------------

@router.get("/contractors/{company_id}/awards", response_model=ContractorAwardsPage)
async def contractor_awards(
    company_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    offset = (page - 1) * page_size
    rc = await db.execute(text("""
        SELECT COUNT(*) FROM award_records_v2
        WHERE contractor_name ILIKE :cid OR canonical_contractor_id::text = :cid2
    """), {"cid": f"%{company_id}%", "cid2": company_id})
    total = rc.scalar() or 0

    r = await db.execute(text("""
        SELECT id, tender_id, contractor_name, amount_bdt, award_date, agency_code
        FROM award_records_v2
        WHERE contractor_name ILIKE :cid OR canonical_contractor_id::text = :cid2
        ORDER BY award_date DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """), {"cid": f"%{company_id}%", "cid2": company_id,
           "limit": page_size, "offset": offset})

    return {
        "total": total, "page": page, "page_size": page_size,
        "awards": [
            {
                "award_id": str(row["id"]),
                "tender_id": row["tender_id"] or "",
                "award_date": row["award_date"],
                "contract_value": _dec(row["amount_bdt"] or 0),
                "category": "Construction",
                "status": "completed",
                "agency": row["agency_code"] or "",
            }
            for row in r.mappings().all()
        ],
    }


# ---------------------------------------------------------------------------
# 3. Contractor Eligibility
# ---------------------------------------------------------------------------

@router.get("/contractors/{company_id}/eligibility", response_model=ContractorEligibilityResponse)
async def contractor_eligibility(
    company_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    rc = await db.execute(text("""
        SELECT COUNT(*) AS cnt, SUM(amount_bdt) AS total
        FROM award_records_v2
        WHERE contractor_name ILIKE :cid OR canonical_contractor_id::text = :cid2
    """), {"cid": f"%{company_id}%", "cid2": company_id})
    s = rc.mappings().first()
    awards = s["cnt"] or 0
    total_value = s["total"] or 0
    
    return ContractorEligibilityResponse(
        rule_37_experience="met" if awards >= 5 else "gap",
        rule_38_financial="met" if total_value > 1e8 else "gap",
        rule_40_technical="met" if awards >= 3 else "gap",
    )


# ---------------------------------------------------------------------------
# 4. Contractor Risk
# ---------------------------------------------------------------------------

@router.get("/contractors/{company_id}/risk", response_model=ContractorRiskProfileResponse)
async def contractor_risk(
    company_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    rc = await db.execute(text("""
        SELECT COUNT(*) AS cnt, AVG(amount_bdt) AS avg_val
        FROM award_records_v2
        WHERE contractor_name ILIKE :cid OR canonical_contractor_id::text = :cid2
    """), {"cid": f"%{company_id}%", "cid2": company_id})
    s = rc.mappings().first()
    awards = s["cnt"] or 0
    avg_val = s["avg_val"] or 0
    
    return ContractorRiskProfileResponse(
        compliance_risk="low" if awards > 10 else "medium",
        market_risk="medium",
        financial_risk="low" if avg_val > 5e7 else "medium",
        operational_risk="low" if awards > 5 else "high",
        overall_risk="low" if awards > 10 else "medium",
        flags=[],
    )


# ---------------------------------------------------------------------------
# 5. Contractor Opportunities
# ---------------------------------------------------------------------------

@router.get("/contractors/{company_id}/opportunities", response_model=list[ContractorOpportunityItem])
async def contractor_opportunities(
    company_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    r = await db.execute(text("""
        SELECT tender_id, title, agency_code, estimated_cost_bdt
        FROM canonical_tenders
        ORDER BY estimated_cost_bdt DESC NULLS LAST LIMIT 5
    """))
    return [
        {
            "tender_id": row["tender_id"],
            "match_score": 0.75,
            "reason": f"Active tender at {row['agency_code']} - "
                      f"est {_dec(row['estimated_cost_bdt'] or 0):,.0f} BDT",
            "partner_recommendation": None,
        }
        for row in r.mappings().all()
    ]
