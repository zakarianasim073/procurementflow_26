"""Phase 2: Tender Matching & Qualification Engine.

Routes:
  /api/v1/tender/{tender_id}/qualify/{contractor_id} - Bid qualification score
  /api/v1/tender/{tender_id}/similar-contractors - Find similar contractors
  /api/v1/tender/{tender_id}/verify/{contractor_id} - Certificate verification
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_async_session

router = APIRouter(tags=["tender-matching"])


async def _ensure_qualification_table(db) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS tender_qualification_scores (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tender_id TEXT NOT NULL,
            contractor_id TEXT NOT NULL,
            contractor_name TEXT,
            qualification_score NUMERIC(5,2) NOT NULL,
            recommendation TEXT NOT NULL,
            confidence_pct NUMERIC(5,2) NOT NULL,
            factors JSONB NOT NULL DEFAULT '{}'::jsonb,
            risk_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
            explanation TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_tender_qualification_scores_tender
        ON tender_qualification_scores (tender_id, created_at DESC)
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_tender_qualification_scores_contractor
        ON tender_qualification_scores (contractor_id, created_at DESC)
    """))


# ── Models ────────────────────────────────────────────────────────────

class TenderQualificationScore(BaseModel):
    tender_id: str
    contractor_id: str
    contractor_name: Optional[str] = None
    qualification_score: float = Field(..., ge=0, le=100, description="0-100 composite score")
    recommendation: str = Field(..., description="BID | CONSIDER | NO-BID")
    confidence_pct: float = Field(..., description="Confidence in recommendation")
    factors: Dict[str, Any] = Field(..., description="Individual factor scores")
    risk_factors: List[str] = Field(default=[], description="Risk warnings")
    explanation: str = Field(..., description="Human-readable recommendation text")

class SimilarContractorMatch(BaseModel):
    contractor_id: str
    contractor_name: str
    similarity_score: float = Field(..., ge=0, le=100)
    similar_projects_count: int
    average_project_value: float
    execution_score: float
    completion_rate: float
    certificates_count: int
    work_type_match: str

class CertificateVerification(BaseModel):
    certificate_no: str
    contractor_name: str
    is_valid: bool
    verification_status: str = Field(..., description="VERIFIED | INVALID | DUPLICATE | NOT_FOUND")
    package_no: Optional[str] = None
    tender_id: Optional[str] = None
    agency_code: Optional[str] = None
    contract_value_bdt: Optional[float] = None
    contract_start_date: Optional[str] = None
    contract_end_date: Optional[str] = None
    completion_status: Optional[str] = None
    reason: Optional[str] = None
    duplicate_count: int = 0

class CertificateVerificationReport(BaseModel):
    contractor_id: str
    contractor_name: str
    total_certificates: int
    verified_count: int
    invalid_count: int
    duplicate_count: int
    not_found_count: int
    certificates: List[CertificateVerification]


# ── 2.1 Tender Qualification Engine ───────────────────────────────────

async def _score_similar_work(db, contractor_id: str, tender_title: str, tender_value: float) -> tuple:
    """Score: has contractor done similar work? (0-100)"""
    # Extract keywords from tender title
    keywords = []
    t_lower = tender_title.lower()
    keyword_map = {
        "road": ["road", "highway", "bridge", "culvert", "embankment"],
        "building": ["building", "construction", "academic", "school", "college"],
        "water": ["water", "drainage", "sewer", "pipeline", "irrigation", "dredging"],
        "electrical": ["electrical", "power", "substation", "cable", "transmission"],
        "maintenance": ["maintenance", "repair", "rehabilitation", "restoration"],
    }
    for category, words in keyword_map.items():
        if any(w in t_lower for w in words):
            keywords.extend(words)

    if not keywords:
        keywords = [tender_title.split()[0]] if tender_title else ["construction"]

    work_type_pattern = f"%{tender_title.split()[0] if tender_title else ''}%"

    # Query similar work
    result = await db.execute(
        text("""
            SELECT cws.total_projects, cws.total_value_bdt, cws.completion_rate,
                   cws.work_type, cws.keyword
            FROM contractor_work_similarity cws
            JOIN contractors c ON c.contractor_name = cws.contractor_name
            WHERE c.id = :contractor_id
              AND (cws.keyword = ANY(:keywords) OR cws.work_type ILIKE :work_type)
            ORDER BY cws.total_projects DESC
            LIMIT 5
        """),
        {"contractor_id": contractor_id, "keywords": keywords, "work_type": work_type_pattern}
    )

    rows = result.mappings().all()
    if not rows:
        return 20, 0, 0  # Some credit for attempt, no similar work

    total_similar = sum(r['total_projects'] for r in rows)
    avg_similar_value = sum(r['total_value_bdt'] for r in rows) / max(total_similar, 1)
    avg_completion = sum(r['completion_rate'] for r in rows) / len(rows)

    # Score based on count + value relevance + completion
    count_score = min(total_similar / 10 * 100, 100)
    value_relevance = min(avg_similar_value / max(tender_value, 1) * 100, 100)
    comp_score = avg_completion * 100

    return (count_score * 0.4 + value_relevance * 0.3 + comp_score * 0.3), total_similar, avg_similar_value


async def _score_agency_familiarity(db, contractor_id: str, agency_code: str) -> tuple:
    """Score: familiarity with this agency? (0-100)"""
    if not agency_code or agency_code == 'UNKNOWN':
        return 50, 0, 0, 0  # Neutral for unknown agency

    result = await db.execute(
        text("""
            SELECT cae.total_projects, cae.completed_projects, cae.on_time_rate,
                   cae.total_value_bdt, cae.avg_delay_days
            FROM contractor_agency_experience cae
            JOIN contractors c ON c.contractor_name = cae.contractor_name
            WHERE c.id = :contractor_id AND cae.agency_code = :agency_code
        """),
        {"contractor_id": contractor_id, "agency_code": agency_code}
    )

    row = result.mappings().first()
    if not row:
        return 40, 0, 0, 0  # No experience with this agency

    on_time = row['on_time_rate'] or 0
    total = row['total_projects'] or 0
    value = row['total_value_bdt'] or 0
    delay = row['avg_delay_days'] or 0

    # Score: on-time performance (50%) + volume (30%) + value (20%)
    return (
        on_time * 50 + min(total / 5 * 100, 30) + min(value / 1e8 * 100, 20),
        total, on_time, delay
    )


async def _score_capacity(db, contractor_id: str, tender_value: float) -> tuple:
    """Score: can contractor handle this workload? (0-100)"""
    result = await db.execute(
        text("""
            SELECT cc.concurrent_projects, cc.current_workload_bdt,
                   cc.total_award_value_bdt, cc.available_capacity_score,
                   cf.annual_turnover_estimate_bdt, cf.financial_exposure_bdt
            FROM contractor_capacity cc
            JOIN contractors c ON c.contractor_name = cc.contractor_name
            LEFT JOIN contractor_finance cf ON c.contractor_name = cf.contractor_name
            WHERE c.id = :contractor_id
        """),
        {"contractor_id": contractor_id}
    )

    row = result.mappings().first()
    if not row:
        return 50, 0, 0, 0  # No data, neutral

    concurrent = row['concurrent_projects'] or 0
    workload = row['current_workload_bdt'] or 0
    total_award = row['total_award_value_bdt'] or 1
    available = row['available_capacity_score'] or 50
    annual = row['annual_turnover_estimate_bdt'] or 1
    exposure = row['financial_exposure_bdt'] or 0

    # Resource saturation (max 8 concurrent projects assumed)
    resource_sat = min(concurrent / 8 * 100, 100)
    resource_score = max(0, 100 - resource_sat)

    # Financial capacity: can they afford this tender?
    leverage = (exposure + tender_value) / max(annual, 1)
    if leverage > 2.0:
        financial_score = 20
    elif leverage > 1.5:
        financial_score = 40
    elif leverage > 1.0:
        financial_score = 60
    else:
        financial_score = 100

    # Available capacity score
    avail_score = available if available else 50

    return (resource_score * 0.4 + financial_score * 0.3 + avail_score * 0.3), concurrent, workload, leverage


async def _score_financial_health(db, contractor_id: str, tender_value: float) -> tuple:
    """Score: financial stability (0-100)"""
    result = await db.execute(
        text("""
            SELECT cf.annual_turnover_estimate_bdt, cf.financial_exposure_bdt,
                   cf.total_award_value_bdt, cf.project_value_std_dev
            FROM contractor_finance cf
            JOIN contractors c ON c.contractor_name = cf.contractor_name
            WHERE c.id = :contractor_id
        """),
        {"contractor_id": contractor_id}
    )

    row = result.mappings().first()
    if not row:
        return 50, 0, 0  # No data, neutral

    annual = row['annual_turnover_estimate_bdt'] or 1
    exposure = row['financial_exposure_bdt'] or 0
    std_dev = row['project_value_std_dev'] or 0

    leverage = exposure / max(annual, 1)
    if leverage > 2.5:
        lev_score = 20
    elif leverage > 2.0:
        lev_score = 40
    elif leverage > 1.0:
        lev_score = 60
    else:
        lev_score = 80

    # Stability: low std_dev relative to mean = stable
    avg_val = row['total_award_value_bdt'] or 1
    cv = std_dev / max(avg_val / 10, 1)  # coefficient of variation
    stability = max(0, 100 - cv * 100)

    return (lev_score * 0.6 + stability * 0.4), leverage, stability


async def _score_execution_history(db, contractor_id: str) -> tuple:
    """Score: overall track record (0-100)"""
    result = await db.execute(
        text("""
            SELECT cd.execution_score, cd.completion_rate, cd.on_time_rate,
                   cd.reliability_score, cd.total_contracts
            FROM contractor_dna cd
            WHERE cd.contractor_id = :contractor_id
        """),
        {"contractor_id": contractor_id}
    )

    row = result.mappings().first()
    if not row:
        return 50, 0, 0, 0, 0

    return (
        row['execution_score'] or 50,
        row['completion_rate'] or 0,
        row['on_time_rate'] or 0,
        row['reliability_score'] or 0,
        row['total_contracts'] or 0
    )


@router.get("/tender/{tender_id}/qualify/{contractor_id}", response_model=TenderQualificationScore)
async def tender_qualify(tender_id: str, contractor_id: str, db: AsyncSession = Depends(get_async_session)):
    """Score contractor fit for tender (0-100). Returns BID/CONSIDER/NO-BID recommendation.

    Factors:
    - Similar work match (25%)
    - Agency familiarity (20%)
    - Capacity available (20%)
    - Financial health (15%)
    - Execution track record (20%)
    """
    # Get tender info
    result = await db.execute(
        text("""
            SELECT package_no, title, agency_code, 
                   0 as estimated_value
            FROM procurement_tenders
            WHERE id = :tender_id OR package_no = :tender_id2
            LIMIT 1
        """),
        {"tender_id": tender_id, "tender_id2": tender_id}
    )

    tender = result.mappings().first()
    if not tender:
        # Try award_records_v2
        result = await db.execute(
            text("""
                SELECT package_no, title, agency_code, amount_bdt as estimated_value
                FROM award_records_v2
                WHERE tender_id = :tender_id OR package_no = :tender_id2
                LIMIT 1
            """),
            {"tender_id": tender_id, "tender_id2": tender_id}
        )
        tender = result.mappings().first()

    if not tender:
        tender = {'package_no': tender_id, 'title': 'Unknown', 'agency_code': 'UNKNOWN', 'estimated_value': 0}

    # Get contractor name
    result = await db.execute(
        text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"),
        {"contractor_id": contractor_id}
    )
    c_row = result.mappings().first()
    contractor_name = c_row['contractor_name'] if c_row else 'Unknown'

    # Score each factor
    similar_score, similar_count, similar_avg = await _score_similar_work(db, contractor_id, tender['title'], tender['estimated_value'])
    agency_score, agency_projects, agency_ot, agency_delay = await _score_agency_familiarity(db, contractor_id, tender['agency_code'])
    capacity_score, concurrent, workload, leverage = await _score_capacity(db, contractor_id, tender['estimated_value'])
    financial_score, fin_leverage, stability = await _score_financial_health(db, contractor_id, tender['estimated_value'])
    exec_score, comp_rate, ot_rate, reliability, total_contracts = await _score_execution_history(db, contractor_id)

    # Weighted composite
    qualification_score = (
        similar_score * 0.25 +
        agency_score * 0.20 +
        capacity_score * 0.20 +
        financial_score * 0.15 +
        exec_score * 0.20
    )

    # Recommendation
    if qualification_score > 75:
        recommendation = "BID"
        confidence = qualification_score
    elif qualification_score > 60:
        recommendation = "CONSIDER"
        confidence = qualification_score
    elif qualification_score > 40:
        recommendation = "RISKY_BID"
        confidence = 100 - qualification_score
    else:
        recommendation = "NO-BID"
        confidence = 100 - qualification_score

    # Risk factors
    risk_factors = []
    if capacity_score < 50:
        risk_factors.append("Capacity constrained")
    if financial_score < 50:
        risk_factors.append("Financial risk elevated")
    if exec_score < 60:
        risk_factors.append("Poor execution track record")
    if agency_score < 40:
        risk_factors.append("No agency experience")
    if similar_score < 30:
        risk_factors.append("No similar work experience")

    # Explanation
    if recommendation == "BID":
        explanation = f"Strong fit — contractor has {total_contracts} projects with {agency_score:.0f}% agency familiarity and {similar_count} similar projects."
    elif recommendation == "CONSIDER":
        explanation = f"Good fit — moderate experience ({total_contracts} projects) but consider risk factors."
    elif recommendation == "RISKY_BID":
        explanation = f"Weak fit — significant gaps in experience or capacity. High risk."
    else:
        explanation = f"Poor fit — insufficient experience, capacity, or financial stability for this tender."

    response = TenderQualificationScore(
        tender_id=tender_id,
        contractor_id=contractor_id,
        contractor_name=contractor_name,
        qualification_score=round(qualification_score, 1),
        recommendation=recommendation,
        confidence_pct=round(confidence, 1),
        factors={
            "similar_work_score": round(similar_score, 1),
            "similar_projects_count": similar_count,
            "similar_avg_value": round(similar_avg, 0),
            "agency_familiarity_score": round(agency_score, 1),
            "agency_projects_count": agency_projects,
            "agency_on_time_rate": round(agency_ot, 1),
            "capacity_score": round(capacity_score, 1),
            "concurrent_projects": concurrent,
            "current_workload_bdt": round(workload, 0),
            "leverage_ratio": round(leverage, 2),
            "financial_health_score": round(financial_score, 1),
            "financial_leverage": round(fin_leverage, 2),
            "stability_score": round(stability, 1),
            "execution_score": round(exec_score, 1),
            "completion_rate": round(comp_rate * 100, 1),
            "on_time_rate": round(ot_rate * 100, 1),
            "reliability_score": round(reliability, 1),
            "total_contracts": total_contracts
        },
        risk_factors=risk_factors,
        explanation=explanation
    )
    await _ensure_qualification_table(db)
    await db.execute(
        text("""
            INSERT INTO tender_qualification_scores (
                tender_id, contractor_id, contractor_name, qualification_score,
                recommendation, confidence_pct, factors, risk_factors, explanation
            )
            VALUES (:tender_id, :contractor_id, :contractor_name, :qualification_score, :recommendation, :confidence_pct, :factors::jsonb, :risk_factors::jsonb, :explanation)
        """),
        {
            "tender_id": response.tender_id,
            "contractor_id": response.contractor_id,
            "contractor_name": response.contractor_name,
            "qualification_score": response.qualification_score,
            "recommendation": response.recommendation,
            "confidence_pct": response.confidence_pct,
            "factors": json.dumps(response.factors),
            "risk_factors": json.dumps(response.risk_factors),
            "explanation": response.explanation,
        }
    )
    await db.commit()
    return response


# ── 2.2 Similar Work Matching ───────────────────────────────────────

@router.get("/tender/{tender_id}/similar-contractors")
async def similar_contractors(
    tender_id: str,
    work_type: Optional[str] = Query(None, description="Override work type (e.g., Road, Building, Water)"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session)
):
    """Find contractors who have done similar work to this tender.

    Returns ranked list with similarity score (0-100), project counts, execution scores.
    """
    # Get tender info
    result = await db.execute(
        text("""
            SELECT title, agency_code, 0 as value
            FROM procurement_tenders
            WHERE id = :tender_id OR package_no = :tender_id2
            LIMIT 1
        """),
        {"tender_id": tender_id, "tender_id2": tender_id}
    )
    tender = result.mappings().first()

    if not tender:
        result = await db.execute(
            text("""
                SELECT title, agency_code, amount_bdt as value
                FROM award_records_v2
                WHERE tender_id = :tender_id OR package_no = :tender_id2
                LIMIT 1
            """),
            {"tender_id": tender_id, "tender_id2": tender_id}
        )
        tender = result.mappings().first()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    tender_value = tender['value'] or 0
    tender_title = tender['title'] or ''
    tender_agency = tender['agency_code'] or 'UNKNOWN'

    # Detect work type from title if not provided
    if not work_type:
        t_lower = tender_title.lower()
        if any(w in t_lower for w in ["road", "highway", "bridge", "culvert", "embankment"]):
            work_type = "Road & Highway"
        elif any(w in t_lower for w in ["building", "construction", "academic", "school"]):
            work_type = "Building Construction"
        elif any(w in t_lower for w in ["water", "drainage", "sewer", "pipeline", "irrigation"]):
            work_type = "Water & Drainage"
        elif any(w in t_lower for w in ["electrical", "power", "substation", "cable"]):
            work_type = "Electrical & Power"
        elif any(w in t_lower for w in ["maintenance", "repair", "rehabilitation"]):
            work_type = "Maintenance & Repair"
        else:
            work_type = "General Construction"

    # Find similar contractors
    result = await db.execute(
        text("""
            SELECT 
                c.id as contractor_id,
                c.contractor_name,
                cws.total_projects,
                cws.total_value_bdt,
                cws.avg_contract_value,
                cws.completion_rate,
                cws.keyword as work_type_match,
                cd.execution_score,
                cd.total_contracts as all_contracts
            FROM contractor_work_similarity cws
            JOIN contractors c ON c.contractor_name = cws.contractor_name
            LEFT JOIN contractor_dna cd ON c.id = cd.contractor_id
            WHERE cws.work_type = :work_type
            ORDER BY cws.total_value_bdt DESC, cd.execution_score DESC NULLS LAST
            LIMIT :limit
        """),
        {"work_type": work_type, "limit": limit}
    )

    results = []
    for row in result.mappings().all():
        total_projects = row['total_projects'] or 0
        total_value = row['total_value_bdt'] or 0
        avg_value = row['avg_contract_value'] or 0
        comp_rate = row['completion_rate'] or 0
        exec_score = row['execution_score'] or 50

        # Compute similarity score
        value_similarity = max(0, 100 - abs(avg_value - tender_value) / max(tender_value, 1) * 100)
        experience_score = min(total_projects / 5 * 100, 100)

        similarity_score = value_similarity * 0.4 + experience_score * 0.35 + exec_score * 0.25

        results.append(SimilarContractorMatch(
            contractor_id=row['contractor_id'],
            contractor_name=row['contractor_name'],
            similarity_score=round(similarity_score, 1),
            similar_projects_count=total_projects,
            average_project_value=round(avg_value, 0),
            execution_score=round(exec_score, 1),
            completion_rate=round(comp_rate * 100, 1),
            certificates_count=0,  # Could be enhanced with cert count
            work_type_match=row['work_type_match'] or work_type
        ))

    # Sort by similarity score descending
    results.sort(key=lambda x: x.similarity_score, reverse=True)

    return {
        "tender_id": tender_id,
        "work_type": work_type,
        "tender_value_bdt": tender_value,
        "count": len(results),
        "results": results
    }


# ── 2.3 Experience Certificate Verification ───────────────────────────

@router.get("/verify/certificate/{certificate_no}")
async def verify_certificate(
    certificate_no: str,
    contractor_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session)
):
    """Verify if an experience certificate is authentic.

    Checks:
    - Certificate exists in registry
    - Not duplicated across contractors
    - Contractor match (if provided)
    """
    # Lookup certificate
    result = await db.execute(
        text("""
            SELECT certificate_no, contractor_name, package_no, tender_id,
                   agency_code, contract_value_bdt, contract_start_date,
                   contract_end_date, completion_status, is_valid, duplicate_count
            FROM experience_certificate_registry
            WHERE certificate_no = :certificate_no
        """),
        {"certificate_no": certificate_no}
    )

    row = result.mappings().first()
    if not row:
        return CertificateVerification(
            certificate_no=certificate_no,
            contractor_name="",
            is_valid=False,
            verification_status="NOT_FOUND",
            reason="Certificate not found in registry"
        )

    # Check if contractor_id matches (if provided)
    if contractor_id:
        result = await db.execute(
            text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"),
            {"contractor_id": contractor_id}
        )
        c_row = result.mappings().first()
        if c_row and c_row['contractor_name'] != row['contractor_name']:
            return CertificateVerification(
                certificate_no=certificate_no,
                contractor_name=row['contractor_name'],
                is_valid=False,
                verification_status="INVALID",
                package_no=row['package_no'],
                tender_id=row['tender_id'],
                agency_code=row['agency_code'],
                contract_value_bdt=row['contract_value_bdt'],
                contract_start_date=row['contract_start_date'],
                contract_end_date=row['contract_end_date'],
                completion_status=row['completion_status'],
                reason=f"Certificate belongs to {row['contractor_name']}, not the claimed contractor",
                duplicate_count=row['duplicate_count'] or 0
            )

    # Check duplicate count
    if row['duplicate_count'] and row['duplicate_count'] > 0:
        return CertificateVerification(
            certificate_no=certificate_no,
            contractor_name=row['contractor_name'],
            is_valid=False,
            verification_status="DUPLICATE",
            package_no=row['package_no'],
            tender_id=row['tender_id'],
            agency_code=row['agency_code'],
            contract_value_bdt=row['contract_value_bdt'],
            contract_start_date=row['contract_start_date'],
            contract_end_date=row['contract_end_date'],
            completion_status=row['completion_status'],
            reason=f"Certificate claimed {row['duplicate_count']} times",
            duplicate_count=row['duplicate_count'] or 0
        )

    # Valid certificate
    return CertificateVerification(
        certificate_no=certificate_no,
        contractor_name=row['contractor_name'],
        is_valid=True,
        verification_status="VERIFIED",
        package_no=row['package_no'],
        tender_id=row['tender_id'],
        agency_code=row['agency_code'],
        contract_value_bdt=row['contract_value_bdt'],
        contract_start_date=row['contract_start_date'],
        contract_end_date=row['contract_end_date'],
        completion_status=row['completion_status'],
        duplicate_count=row['duplicate_count'] or 0
    )


@router.get("/verify/contractor/{contractor_id}")
async def verify_all_contractor_certificates(
    contractor_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Verify all certificates for a contractor."""
    # Get contractor name
    result = await db.execute(
        text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"),
        {"contractor_id": contractor_id}
    )
    c_row = result.mappings().first()
    if not c_row:
        raise HTTPException(status_code=404, detail="Contractor not found")

    contractor_name = c_row['contractor_name']

    # Get all certificates for this contractor
    result = await db.execute(
        text("""
            SELECT certificate_no, package_no, tender_id, agency_code,
                   contract_value_bdt, contract_start_date, contract_end_date,
                   completion_status, is_valid, duplicate_count
            FROM experience_certificate_registry
            WHERE contractor_name = :contractor_name
        """),
        {"contractor_name": contractor_name}
    )

    certificates = []
    verified = 0
    invalid = 0
    duplicate = 0
    not_found = 0

    for row in result.mappings().all():
        if row['duplicate_count'] and row['duplicate_count'] > 0:
            status = "DUPLICATE"
            is_valid = False
            duplicate += 1
        elif not row['is_valid']:
            status = "INVALID"
            is_valid = False
            invalid += 1
        else:
            status = "VERIFIED"
            is_valid = True
            verified += 1

        certificates.append(CertificateVerification(
            certificate_no=row['certificate_no'],
            contractor_name=contractor_name,
            is_valid=is_valid,
            verification_status=status,
            package_no=row['package_no'],
            tender_id=row['tender_id'],
            agency_code=row['agency_code'],
            contract_value_bdt=row['contract_value_bdt'],
            contract_start_date=row['contract_start_date'],
            contract_end_date=row['contract_end_date'],
            completion_status=row['completion_status'],
            duplicate_count=row['duplicate_count'] or 0
        ))

    return CertificateVerificationReport(
        contractor_id=contractor_id,
        contractor_name=contractor_name,
        total_certificates=len(certificates),
        verified_count=verified,
        invalid_count=invalid,
        duplicate_count=duplicate,
        not_found_count=not_found,
        certificates=certificates
    )
