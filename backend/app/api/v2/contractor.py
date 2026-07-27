from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, func, select
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_async_session
from app.models.intelligence import Contractor, ContractorDNA, AwardRecordV2

router = APIRouter(tags=["contractor"])


class EligibilityStatus(BaseModel):
    rule_id: str
    rule_title: str
    status: str  # met, gap, exceed
    evidence: Optional[str]


class AwardRecord(BaseModel):
    tender_id: str
    agency: str
    category: str
    award_date: Optional[datetime]
    contract_value: float
    status: str  # completed, ongoing, cancelled


class ContractorProfile(BaseModel):
    name: str
    registration_number: str
    years_operating: int
    status: str
    total_awards: int
    total_value: float
    avg_contract_value: float
    win_rate: float
    eligibility_status: List[EligibilityStatus]
    recent_awards: List[AwardRecord]
    compliance_rate: float
    risk_profile: dict  # compliance, market, financial, operational risk levels
    peer_comparison: dict  # avg metrics for similar contractors


@router.get("/contractor/{company_id}/profile", response_model=ContractorProfile)
async def get_contractor_profile(
    company_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Get full contractor profile with eligibility, experience, awards, and risk."""
    # Query contractor from Contractor table
    contractor = (await db.execute(
        select(Contractor).where(Contractor.id == company_id)
    )).scalars().first()

    # If not found, try querying by name (fallback)
    if not contractor:
        contractor = (await db.execute(
            select(Contractor).where(Contractor.contractor_name.ilike(company_id))
        )).scalars().first()

    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    # Query contractor DNA for advanced metrics
    dna = (await db.execute(
        select(ContractorDNA).where(ContractorDNA.contractor_id == contractor.id)
    )).scalars().first()

    # Query recent awards
    recent_awards_db = (await db.execute(
        select(AwardRecordV2)
        .where(AwardRecordV2.contractor_name == contractor.contractor_name)
        .order_by(desc(AwardRecordV2.award_date))
        .limit(5)
    )).scalars().all()

    recent_awards = [
        AwardRecord(
            tender_id=award.tender_id or award.id,
            agency=award.agency_code or "Unknown",
            category="Construction",  # Default category
            award_date=_parse_date(award.award_date),
            contract_value=award.amount_bdt or 0.0,
            status="completed"
        )
        for award in recent_awards_db
    ]

    # Calculate stats
    win_rate = dna.win_rate if dna else 0.0
    avg_contract = contractor.total_amount_bdt / max(contractor.total_contracts, 1)
    first_award = _parse_date(dna.first_award_date) if dna else None
    years_operating = max(0, (datetime.now() - first_award).days // 365) if first_award else 0

    # Compute peer comparison from actual contractor pool data
    all_contractors = (await db.execute(
        select(func.count(Contractor.id), func.avg(Contractor.avg_npp))
        .select_from(Contractor)
    )).first()
    total_contractors = all_contractors[0] or 1
    all_avg_npp = all_contractors[1] or 0

    # Ranking percentile based on total contract value
    higher_value_count = (await db.execute(
        select(func.count()).select_from(Contractor)
        .where(Contractor.total_amount_bdt > contractor.total_amount_bdt)
    )).scalar() or 0
    percentile_rank = round((1 - higher_value_count / total_contractors) * 100, 1) if total_contractors > 0 else 50

    return ContractorProfile(
        name=contractor.contractor_name,
        registration_number=f"REG-{contractor.id[:8]}",
        years_operating=years_operating,
        status="active",
        total_awards=contractor.total_contracts,
        total_value=contractor.total_amount_bdt,
        avg_contract_value=avg_contract,
        win_rate=win_rate,
        eligibility_status=[
            EligibilityStatus(
                rule_id="R37",
                rule_title="Experience Qualification",
                status="meet" if contractor.total_contracts >= 5 else "gap",
                evidence=f"{contractor.total_contracts} contracts completed"
            ),
        ],
        recent_awards=recent_awards,
        compliance_rate=dna.health_score * 100 if dna else 85.0,
        risk_profile={
            "compliance": "low" if (dna and dna.health_score > 0.7) else "medium",
            "market": "medium",
            "financial": "low" if contractor.total_amount_bdt > 1e8 else "medium",
            "operational": "low"
        },
        peer_comparison={
            "avg_win_rate": round(all_avg_npp * 100, 1) if all_avg_npp else round(win_rate * 100, 1),
            "avg_contract_value": f"₹{all_avg_npp/1e7:.1f} Cr" if all_avg_npp else f"₹{avg_contract/1e7:.1f} Cr",
            "your_ranking": f"top {percentile_rank}%"
        }
    )


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string (YYYY-MM-DD format) to datetime."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None
