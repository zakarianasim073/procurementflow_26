"""Phase 4: Advanced Intelligence — Tender Recommendation Engine + Delay Prediction + Network Graph.

Routes:
  /api/v1/tender/{id}/recommend/{contractor_id}   - Comprehensive bid recommendation
  /api/v1/predict/delay/{contractor_id}           - ML delay prediction
  /api/v1/network/contractor/{contractor_id}       - Experience network graph
  /api/v1/network/similar/{contractor_id}           - Find similar contractors via graph
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import statistics
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_async_session

router = APIRouter(tags=["advanced-intelligence"])


# ── Models ────────────────────────────────────────────────────────────

class TenderRecommendation(BaseModel):
    tender_id: str
    contractor_id: str
    contractor_name: str
    recommendation: str = Field(..., description="BID | CONSIDER | NO-BID")
    recommendation_score: float = Field(..., ge=0, le=100)
    confidence_pct: float = Field(..., ge=0, le=100)
    win_probability_estimate: float = Field(..., ge=0, le=100)
    recommended_bid_amount: float
    factors: Dict[str, Any]
    risk_factors: List[str]
    explanation: str

class DelayPrediction(BaseModel):
    contractor_id: str
    contractor_name: str
    agency: str
    work_type: str
    expected_delay_days: float
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH")
    confidence_interval_low: float
    confidence_interval_high: float
    recommendation: str

class NetworkNode(BaseModel):
    id: str
    label: str
    type: str  # contractor | agency | district | work_type
    value: Optional[float] = None

class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: float
    type: str  # worked_with | similar_to

class ExperienceNetwork(BaseModel):
    contractor_id: str
    contractor_name: str
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    similar_contractors: List[Dict[str, Any]]


# ── 4.2 Tender Recommendation Engine ─────────────────────────────────

@router.get("/tender/{tender_id}/recommend/{contractor_id}", response_model=TenderRecommendation)
async def tender_recommend(
    tender_id: str,
    contractor_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Comprehensive bid/no-bid recommendation synthesizing ALL intelligence.
    
    Combines:
    - Tender qualification (Phase 2)
    - Capacity analysis (Phase 3)
    - Financial risk (Phase 3)
    - Similar work matching (Phase 2)
    - Execution history (Phase 1)
    
    Returns: recommendation, score, win probability, risk factors, recommended bid amount.
    """
    
    # Get tender info
    result = await db.execute(text("""
        SELECT package_no, title, agency_code, 0 as estimated_value
        FROM procurement_tenders
        WHERE id = :tender_id OR package_no = :tender_id
        LIMIT 1
    """), {"tender_id": tender_id})
    tender = result.mappings().first()
    if not tender:
        result = await db.execute(text("""
            SELECT package_no, title, agency_code, amount_bdt as estimated_value
            FROM award_records_v2
            WHERE tender_id = :tender_id OR package_no = :tender_id
            LIMIT 1
        """), {"tender_id": tender_id})
        tender = result.mappings().first()
    if not tender:
        tender = {'package_no': tender_id, 'title': 'Unknown', 'agency_code': 'UNKNOWN', 'estimated_value': 0}
    
    tender_value = tender['estimated_value'] or 0
    tender_agency = tender['agency_code'] or 'UNKNOWN'
    tender_title = tender['title'] or ''
    
    # Get contractor name
    result = await db.execute(text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})
    c_row = result.mappings().first()
    contractor_name = c_row['contractor_name'] if c_row else 'Unknown'
    
    # ── Factor 1: Similar Work (25%) ────────────────────────────
    t_lower = tender_title.lower()
    work_keywords = []
    keyword_map = {
        "road": ["road", "highway", "bridge", "culvert", "embankment"],
        "building": ["building", "construction", "academic", "school"],
        "water": ["water", "drainage", "sewer", "pipeline", "irrigation"],
        "electrical": ["electrical", "power", "substation", "cable"],
    }
    for cat, words in keyword_map.items():
        if any(w in t_lower for w in words):
            work_keywords.extend(words)
    if not work_keywords:
        work_keywords = [tender_title.split()[0]] if tender_title else ["construction"]
    
    keyword_pattern = f"%{work_keywords[0]}%"
    result = await db.execute(text("""
        SELECT cws.total_projects, cws.total_value_bdt, cws.completion_rate
        FROM contractor_work_similarity cws
        JOIN contractors c ON c.contractor_name = cws.contractor_name
        WHERE c.id = :contractor_id AND (cws.keyword = ANY(:keywords) OR cws.work_type ILIKE :keyword_pattern)
        ORDER BY cws.total_value_bdt DESC LIMIT 1
    """), {"contractor_id": contractor_id, "keywords": work_keywords, "keyword_pattern": keyword_pattern})
    similar_row = result.mappings().first()
    if similar_row:
        similar_count = similar_row['total_projects'] or 0
        similar_value = similar_row['total_value_bdt'] or 0
        similar_comp = similar_row['completion_rate'] or 0
        count_score = min(similar_count / 10 * 100, 100)
        value_score = min(similar_value / max(tender_value, 1) * 100, 100)
        comp_score = similar_comp * 100
        similar_score = (count_score * 0.4 + value_score * 0.3 + comp_score * 0.3)
    else:
        similar_score = 20
        similar_count = 0
        similar_value = 0
    
    # ── Factor 2: Agency Familiarity (20%) ─────────────────────
    if tender_agency and tender_agency != 'UNKNOWN':
        result = await db.execute(text("""
            SELECT total_projects, completed_projects, on_time_rate, total_value_bdt
            FROM contractor_agency_experience
            WHERE contractor_name = :contractor_name AND agency_code = :agency_code
        """), {"contractor_name": contractor_name, "agency_code": tender_agency})
        agency_row = result.mappings().first()
        if agency_row:
            agency_total = agency_row['total_projects'] or 0
            agency_ot = agency_row['on_time_rate'] or 0
            agency_value = agency_row['total_value_bdt'] or 0
            agency_score = (agency_ot * 50 + min(agency_total / 5 * 100, 30) + min(agency_value / 1e8 * 100, 20))
        else:
            agency_score = 40
            agency_total = 0
    else:
        agency_score = 50
        agency_total = 0
    
    # ── Factor 3: Capacity (20%) ───────────────────────────────
    result = await db.execute(text("""
        SELECT cc.concurrent_projects, cc.current_workload_bdt,
               cc.total_award_value_bdt, cc.available_capacity_score,
               cf.annual_turnover_estimate_bdt, cf.financial_exposure_bdt
        FROM contractors c
        LEFT JOIN contractor_capacity cc ON c.contractor_name = cc.contractor_name
        LEFT JOIN contractor_finance cf ON c.contractor_name = cf.contractor_name
        WHERE c.id = :contractor_id
    """), {"contractor_id": contractor_id})
    cap_row = result.mappings().first()
    if cap_row:
        concurrent = cap_row['concurrent_projects'] or 0
        workload = cap_row['current_workload_bdt'] or 0
        available = cap_row['available_capacity_score'] or 50
        annual = cap_row['annual_turnover_estimate_bdt'] or 1
        exposure = cap_row['financial_exposure_bdt'] or 0
        
        resource_sat = min(concurrent / 8 * 100, 100)
        resource_score = max(0, 100 - resource_sat)
        
        leverage = (exposure + tender_value) / max(annual, 1)
        if leverage > 2.0: fin_score = 20
        elif leverage > 1.5: fin_score = 40
        elif leverage > 1.0: fin_score = 60
        else: fin_score = 100
        
        capacity_score = resource_score * 0.4 + fin_score * 0.3 + (available or 50) * 0.3
    else:
        capacity_score = 50
        concurrent = 0
        workload = 0
        leverage = 0
    
    # ── Factor 4: Financial Health (15%) ───────────────────────
    result = await db.execute(text("""
        SELECT annual_turnover_estimate_bdt, financial_exposure_bdt, total_award_value_bdt, project_value_std_dev
        FROM contractor_finance cf
        JOIN contractors c ON c.contractor_name = cf.contractor_name
        WHERE c.id = :contractor_id
    """), {"contractor_id": contractor_id})
    fin_row = result.mappings().first()
    if fin_row:
        annual = fin_row['annual_turnover_estimate_bdt'] or 1
        exposure = fin_row['financial_exposure_bdt'] or 0
        std_dev = fin_row['project_value_std_dev'] or 0
        leverage = exposure / max(annual, 1)
        if leverage > 2.5: lev_score = 20
        elif leverage > 2.0: lev_score = 40
        elif leverage > 1.0: lev_score = 60
        else: lev_score = 80
        
        avg_val = fin_row['total_award_value_bdt'] or 1
        cv = std_dev / max(avg_val / 10, 1)
        stability = max(0, 100 - cv * 100)
        financial_score = lev_score * 0.6 + stability * 0.4
    else:
        financial_score = 50
    
    # ── Factor 5: Execution Track Record (20%) ─────────────────
    result = await db.execute(text("""
        SELECT execution_score, completion_rate, on_time_rate, total_contracts, total_amount_bdt
        FROM contractor_dna WHERE contractor_id = :contractor_id
    """), {"contractor_id": contractor_id})
    dna_row = result.mappings().first()
    if dna_row:
        exec_score = dna_row['execution_score'] or 50
        comp_rate = dna_row['completion_rate'] or 0
        ot_rate = dna_row['on_time_rate'] or 0
        total_contracts = dna_row['total_contracts'] or 0
        total_value = dna_row['total_amount_bdt'] or 0
    else:
        exec_score = 50
        comp_rate = 0
        ot_rate = 0
        total_contracts = 0
        total_value = 0
    
    # ── Weighted Composite ──────────────────────────────────────
    recommendation_score = (
        similar_score * 0.25 +
        agency_score * 0.20 +
        capacity_score * 0.20 +
        financial_score * 0.15 +
        exec_score * 0.20
    )
    
    # ── Recommendation ──────────────────────────────────────────
    if recommendation_score > 75:
        recommendation = "BID"
        confidence = recommendation_score
    elif recommendation_score > 60:
        recommendation = "CONSIDER"
        confidence = recommendation_score
    elif recommendation_score > 40:
        recommendation = "RISKY_BID"
        confidence = 100 - recommendation_score
    else:
        recommendation = "NO-BID"
        confidence = 100 - recommendation_score
    
    # ── Win Probability Estimate ────────────────────────────────
    if recommendation_score < 50 or capacity_score < 40:
        win_prob = 20
    elif recommendation_score > 85 and capacity_score > 80:
        win_prob = 70
    else:
        win_prob = 45
    
    # ── Recommended Bid Amount ──────────────────────────────────
    result = await db.execute(text("""
        SELECT AVG(contract_value_bdt) as avg_value
        FROM contractor_execution_history
        WHERE contractor_name = :contractor_name
          AND completion_status ILIKE '%completed%'
    """), {"contractor_name": contractor_name})
    avg_row = result.mappings().first()
    avg_value = avg_row['avg_value'] if avg_row and avg_row['avg_value'] else tender_value
    recommended_bid = avg_value * 0.95 if avg_value > 0 else tender_value
    
    # ── Risk Factors ────────────────────────────────────────────
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
    
    # ── Explanation ───────────────────────────────────────────
    if recommendation == "BID":
        explanation = f"Strong fit — {total_contracts} projects, {exec_score:.0f} execution score, {similar_count} similar projects. Recommend bidding at 95% of similar project average."
    elif recommendation == "CONSIDER":
        explanation = f"Good fit — moderate experience ({total_contracts} projects) with some gaps. Consider bidding with risk mitigation."
    elif recommendation == "RISKY_BID":
        explanation = f"Weak fit — significant gaps in experience, capacity, or financial stability. High risk."
    else:
        explanation = f"Poor fit — insufficient experience, capacity, or financial stability for this tender."
    
    return TenderRecommendation(
        tender_id=tender_id,
        contractor_id=contractor_id,
        contractor_name=contractor_name,
        recommendation=recommendation,
        recommendation_score=round(recommendation_score, 1),
        confidence_pct=round(confidence, 1),
        win_probability_estimate=round(win_prob, 1),
        recommended_bid_amount=round(recommended_bid, 0),
        factors={
            "similar_work_score": round(similar_score, 1),
            "similar_projects_count": similar_count,
            "agency_familiarity_score": round(agency_score, 1),
            "agency_projects_count": agency_total,
            "capacity_score": round(capacity_score, 1),
            "concurrent_projects": concurrent,
            "current_workload_bdt": round(workload, 0),
            "leverage_ratio": round(leverage, 2),
            "financial_health_score": round(financial_score, 1),
            "execution_score": round(exec_score, 1),
            "completion_rate": round(comp_rate * 100, 1),
            "on_time_rate": round(ot_rate * 100, 1),
            "total_contracts": total_contracts,
        },
        risk_factors=risk_factors,
        explanation=explanation
    )


# ── 4.1 Delay Prediction (Heuristic) ─────────────────────────────────

@router.get("/predict/delay/{contractor_id}")
async def predict_delay(
    contractor_id: str,
    agency: str = Query("LGED", description="Agency code"),
    work_type: str = Query("Road & Highway", description="Work type"),
    project_value: float = Query(50000000, description="Project value in BDT"),
    duration_months: int = Query(12, description="Expected duration"),
    db: AsyncSession = Depends(get_async_session)
):
    """Predict expected delay for a contractor-agency-work_type combination.
    
    Uses historical delay patterns from execution_history.
    No ML model required — heuristic based on historical averages.
    """
    
    result = await db.execute(text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})
    c_row = result.mappings().first()
    contractor_name = c_row['contractor_name'] if c_row else 'Unknown'
    
    # Historical delay for this contractor + agency + work_type
    wt_pattern1 = f"%{work_type.split()[0]}%"
    wt_pattern2 = f"%{work_type.split()[-1]}%"
    wt_pattern3 = f"%{work_type}%"
    result = await db.execute(text("""
        SELECT AVG(delay_days) as avg_delay, STDDEV(delay_days) as std_delay,
               COUNT(*) as sample_count
        FROM contractor_execution_history
        WHERE contractor_name = :contractor_name
          AND (agency_code = :agency OR :agency = 'ANY')
          AND (title ILIKE :wt_pattern1 OR title ILIKE :wt_pattern2 OR title ILIKE :wt_pattern3)
    """), {"contractor_name": contractor_name, "agency": agency,
           "wt_pattern1": wt_pattern1, "wt_pattern2": wt_pattern2, "wt_pattern3": wt_pattern3})
    hist = result.mappings().first()
    
    avg_delay = hist['avg_delay'] or 0
    std_delay = hist['std_delay'] or 0
    sample_count = hist['sample_count'] or 0
    
    # If no specific history, use agency-wide average
    if sample_count < 3:
        result = await db.execute(text("""
            SELECT AVG(delay_days) as avg_delay, STDDEV(delay_days) as std_delay
            FROM contractor_execution_history
            WHERE agency_code = :agency
        """), {"agency": agency})
        agency_hist = result.mappings().first()
        if agency_hist and agency_hist['avg_delay']:
            avg_delay = agency_hist['avg_delay']
            std_delay = agency_hist['std_delay'] or 0
    
    # If still no data, use global average
    if avg_delay == 0:
        result = await db.execute(text("SELECT AVG(delay_days) as avg_delay FROM contractor_execution_history"))
        global_avg = result.mappings().first()
        avg_delay = global_avg['avg_delay'] or 0
    
    # Adjust based on project value (larger projects tend to have more delays)
    value_factor = 1.0
    if project_value > 1e9:
        value_factor = 1.5
    elif project_value > 5e8:
        value_factor = 1.3
    elif project_value > 1e8:
        value_factor = 1.1
    
    expected_delay = avg_delay * value_factor
    
    # Confidence interval
    ci_low = max(0, expected_delay - std_delay * 0.674)
    ci_high = expected_delay + std_delay * 0.674
    
    # Risk level
    if expected_delay < 15:
        risk_level = "LOW"
    elif expected_delay < 45:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
    
    return DelayPrediction(
        contractor_id=contractor_id,
        contractor_name=contractor_name,
        agency=agency,
        work_type=work_type,
        expected_delay_days=round(expected_delay, 1),
        risk_level=risk_level,
        confidence_interval_low=round(ci_low, 1),
        confidence_interval_high=round(ci_high, 1),
        recommendation="Monitor closely" if risk_level == "HIGH" else "Acceptable delay range"
    )


# ── 4.3 Experience Network Graph ─────────────────────────────────────

@router.get("/network/contractor/{contractor_id}")
async def contractor_network(
    contractor_id: str,
    max_distance: int = Query(2, ge=1, le=3, description="Graph distance from contractor"),
    db: AsyncSession = Depends(get_async_session)
):
    """Build experience relationship graph for a contractor.
    
    Nodes: Contractors, Agencies, Districts, Work Types
    Edges: (contractor → agency), (contractor → district), (contractor → work_type)
    
    Returns: Network nodes + edges + similar contractors found via shared connections.
    """
    
    result = await db.execute(text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})
    c_row = result.mappings().first()
    if not c_row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    contractor_name = c_row['contractor_name']
    nodes = []
    edges = []
    
    # Root node
    nodes.append(NetworkNode(id=contractor_id, label=contractor_name, type="contractor"))
    
    # Agency connections
    result = await db.execute(text("""
        SELECT agency_code, total_projects, total_value_bdt
        FROM contractor_agency_experience
        WHERE contractor_name = :contractor_name
        ORDER BY total_value_bdt DESC
        LIMIT 10
    """), {"contractor_name": contractor_name})
    for row in result.mappings().all():
        agency_id = f"agency_{row['agency_code']}"
        nodes.append(NetworkNode(id=agency_id, label=row['agency_code'], type="agency", value=row['total_value_bdt']))
        edges.append(NetworkEdge(source=contractor_id, target=agency_id, weight=row['total_projects'] or 1, type="worked_with"))
    
    # District connections
    result = await db.execute(text("""
        SELECT district, total_projects, total_value_bdt
        FROM contractor_district_experience
        WHERE contractor_name = :contractor_name
        ORDER BY total_value_bdt DESC
        LIMIT 10
    """), {"contractor_name": contractor_name})
    for row in result.mappings().all():
        district_id = f"district_{row['district']}"
        nodes.append(NetworkNode(id=district_id, label=row['district'], type="district", value=row['total_value_bdt']))
        edges.append(NetworkEdge(source=contractor_id, target=district_id, weight=row['total_projects'] or 1, type="worked_with"))
    
    # Work type connections
    result = await db.execute(text("""
        SELECT work_type, total_projects, total_value_bdt
        FROM contractor_work_similarity
        WHERE contractor_name = :contractor_name
        ORDER BY total_value_bdt DESC
        LIMIT 10
    """), {"contractor_name": contractor_name})
    for row in result.mappings().all():
        wt_id = f"work_{row['work_type'][:20]}"
        nodes.append(NetworkNode(id=wt_id, label=row['work_type'], type="work_type", value=row['total_value_bdt']))
        edges.append(NetworkEdge(source=contractor_id, target=wt_id, weight=row['total_projects'] or 1, type="worked_with"))
    
    # Find similar contractors via shared agencies (distance 2)
    similar = []
    agency_codes = [e.target for e in edges if e.type == "worked_with" and e.target.startswith("agency_")]
    if agency_codes:
        codes = [a.replace("agency_", "") for a in agency_codes[:5]]  # Top 5 agencies
        result = await db.execute(text("""
            SELECT c.id, c.contractor_name, cae.agency_code, cae.total_projects, cae.total_value_bdt
            FROM contractor_agency_experience cae
            JOIN contractors c ON c.contractor_name = cae.contractor_name
            WHERE cae.agency_code = ANY(:codes) AND c.id != :contractor_id
            ORDER BY cae.total_value_bdt DESC
            LIMIT 10
        """), {"codes": codes, "contractor_id": contractor_id})
        for row in result.mappings().all():
            similar.append({
                "contractor_id": row['id'],
                "contractor_name": row['contractor_name'],
                "connection_type": "shared_agency",
                "shared_agency": row['agency_code'],
                "shared_projects": row['total_projects'],
                "shared_value": row['total_value_bdt']
            })
            # Add edge between similar contractor and shared agency
            sim_id = row['id']
            agency_id = f"agency_{row['agency_code']}"
            if not any(n.id == sim_id for n in nodes):
                nodes.append(NetworkNode(id=sim_id, label=row['contractor_name'], type="contractor"))
            edges.append(NetworkEdge(source=sim_id, target=agency_id, weight=row['total_projects'] or 1, type="similar_to"))
    
    return ExperienceNetwork(
        contractor_id=contractor_id,
        contractor_name=contractor_name,
        nodes=nodes,
        edges=edges,
        similar_contractors=similar
    )
