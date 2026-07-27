"""Phase 5: Advanced Analytics — Award vs Execution, Win Probability, AI Resume Generator.

Routes:
  /api/v1/analytics/award-vs-execution/{contractor_id}    - Variance analysis
  /api/v1/analytics/win-probability/features/{tender_id}/{contractor_id}  - ML features
  /api/v1/analytics/win-probability/training-data          - Export training dataset
  /api/v1/generate/resume/{contractor_id}                  - JSON resume
  /api/v1/generate/resume/{contractor_id}/docx             - DOCX download
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import io
from datetime import datetime, timezone

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_async_session


router = APIRouter(tags=["advanced-analytics"])


# ── Models ────────────────────────────────────────────────────────────

class AwardExecutionVariance(BaseModel):
    tender_id: str
    package_no: Optional[str]
    awarded_amount_bdt: float
    executed_amount_bdt: float
    value_variance_pct: float
    planned_duration_days: Optional[int]
    actual_duration_days: Optional[int]
    delay_days: int
    cost_status: str = Field(..., description="COST_OVERRUN | COST_UNDERRUN | ON_BUDGET")
    schedule_status: str = Field(..., description="DELAYED | ON_TIME")
    agency_code: Optional[str]

class ContractorReliability(BaseModel):
    contractor_id: str
    contractor_name: str
    total_projects: int
    on_budget_pct: float
    on_time_pct: float
    avg_cost_variance_pct: float
    avg_delay_days: float
    reliability_score: float

class WinProbabilityFeatures(BaseModel):
    tender_id: str
    contractor_id: str
    contractor_name: str
    similar_projects_count: int
    similar_projects_avg_value: float
    agency_projects_count: int
    agency_on_time_rate: float
    execution_score: float
    completion_rate: float
    on_time_rate: float
    experience_value_ratio: float
    qualifying_projects_count: int
    market_share_pct: float
    win_probability_estimate: float
    features_vector: List[float]

class ContractorResume(BaseModel):
    contractor_name: str
    organization_type: str = "Contractor"
    executive_summary: str
    total_projects: int
    completed_projects: int
    total_value_bdt: float
    avg_project_value: float
    largest_project: float
    execution_score: float
    completion_rate: float
    on_time_rate: float
    agencies_worked: List[Dict[str, Any]]
    work_experience: List[Dict[str, Any]]
    key_projects: List[Dict[str, Any]]
    certifications: List[Dict[str, Any]]
    financial_profile: Dict[str, Any]
    generated_at: str


# ── 5.1 Award vs Execution Analysis ──────────────────────────────────

@router.get("/analytics/award-vs-execution/{contractor_id}")
async def award_vs_execution(
    contractor_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session)
):
    """Compare award records with actual execution for a contractor.
    
    Identifies:
    - Cost overruns / underruns
    - Schedule delays
    - Budget accuracy patterns
    """
    result = await db.execute(text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})
    c_row = result.mappings().first()
    if not c_row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    contractor_name = c_row['contractor_name']
    
    # Match awards with execution records (join on package_no since ceh has no tender_id)
    # Use DISTINCT ON to pick the latest execution record per package_no, avoiding duplicates
    result = await db.execute(text("""
        SELECT 
            ar.tender_id,
            ar.package_no,
            ar.amount_bdt as awarded_amount,
            ar.agency_code,
            ceh.contract_value_bdt as executed_amount,
            ceh.completed_value_bdt,
            ceh.delay_days,
            ceh.actual_completion_date,
            ceh.planned_completion_date,
            ceh.contract_start_date,
            ceh.contract_end_date
        FROM award_records_v2 ar
        LEFT JOIN (
            SELECT DISTINCT ON (package_no) *
            FROM contractor_execution_history
            WHERE contractor_name = :cname
            ORDER BY package_no, COALESCE(actual_completion_date, contract_end_date, contract_start_date) DESC NULLS LAST
        ) ceh ON ar.package_no = ceh.package_no
        WHERE ar.contractor_name = :cname
          AND ar.amount_bdt IS NOT NULL
        ORDER BY ar.amount_bdt DESC
        LIMIT :limit
    """), {"cname": contractor_name, "limit": limit})
    
    variances = []
    for row in result.mappings().all():
        awarded = row['awarded_amount'] or 0
        executed = row['executed_amount'] or awarded
        
        # Calculate variance
        if awarded > 0 and executed > 0:
            value_variance = ((executed - awarded) / awarded) * 100
        else:
            value_variance = 0
        
        if value_variance > 5:
            cost_status = "COST_OVERRUN"
        elif value_variance < -5:
            cost_status = "COST_UNDERRUN"
        else:
            cost_status = "ON_BUDGET"
        
        delay = row['delay_days'] or 0
        schedule_status = "DELAYED" if delay > 30 else "ON_TIME"
        
        variances.append(AwardExecutionVariance(
            tender_id=row['tender_id'] or "",
            package_no=row['package_no'],
            awarded_amount_bdt=awarded,
            executed_amount_bdt=executed,
            value_variance_pct=round(value_variance, 2),
            planned_duration_days=None,
            actual_duration_days=None,
            delay_days=delay,
            cost_status=cost_status,
            schedule_status=schedule_status,
            agency_code=row['agency_code']
        ))
    
    # Aggregate reliability metrics
    total = len(variances)
    if total > 0:
        on_budget = sum(1 for v in variances if v.cost_status == "ON_BUDGET")
        on_time = sum(1 for v in variances if v.schedule_status == "ON_TIME")
        avg_variance = sum(abs(v.value_variance_pct) for v in variances) / total
        avg_delay = sum(v.delay_days for v in variances) / total
        on_budget_pct = (on_budget / total) * 100
        on_time_pct = (on_time / total) * 100
        reliability = (on_budget_pct + on_time_pct) / 2
    else:
        avg_variance = 0
        avg_delay = 0
        on_budget_pct = 0
        on_time_pct = 0
        reliability = 0
    
    return {
        "contractor_id": contractor_id,
        "contractor_name": contractor_name,
        "total_projects_analyzed": total,
        "summary": {
            "on_budget_pct": round(on_budget_pct, 1),
            "on_time_pct": round(on_time_pct, 1),
            "avg_cost_variance_pct": round(avg_variance, 2),
            "avg_delay_days": round(avg_delay, 1),
            "reliability_score": round(reliability, 1)
        },
        "variances": [v.model_dump() for v in variances]
    }


# ── 5.2 Win Probability Features ─────────────────────────────────────

@router.get("/analytics/win-probability/features/{tender_id}/{contractor_id}")
async def win_probability_features(
    tender_id: str,
    contractor_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Extract ML features for win probability prediction.
    
    Features:
    1. Similar completed projects (count, avg value)
    2. Agency familiarity (projects with agency, on-time rate)
    3. Execution score (overall track record)
    4. Experience value ratio (avg project value / bid value)
    5. Market share (% of awards in category)
    6. Win probability estimate (0-100)
    """
    # Get contractor info
    result = await db.execute(text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})
    c_row = result.mappings().first()
    if not c_row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    contractor_name = c_row['contractor_name']
    
    # Get tender info
    result = await db.execute(text("""
        SELECT package_no, title, agency_code, COALESCE(amount_bdt, 0) as value
        FROM award_records_v2
        WHERE tender_id = :tender_id OR package_no = :tender_id
        LIMIT 1
    """), {"tender_id": tender_id})
    tender = result.mappings().first()
    if not tender:
        tender = {'package_no': tender_id, 'title': '', 'agency_code': 'UNKNOWN', 'value': 0}
    
    tender_value = tender['value'] or 0
    tender_agency = tender['agency_code'] or 'UNKNOWN'
    
    # Feature 1: Similar projects (inferred from title keywords against contractor_work_similarity)
    t_lower = (tender['title'] or '').lower()
    work_type = "General"
    if any(w in t_lower for w in ["road", "highway", "bridge"]):
        work_type = "Road & Highway"
    elif any(w in t_lower for w in ["building", "construction", "school"]):
        work_type = "Building Construction"
    elif any(w in t_lower for w in ["water", "drainage", "sewer"]):
        work_type = "Water & Drainage"
    
    result = await db.execute(text("""
        SELECT total_projects, total_value_bdt, avg_contract_value
        FROM contractor_work_similarity
        WHERE contractor_name = :contractor_name AND work_type = :work_type
    """), {"contractor_name": contractor_name, "work_type": work_type})
    similar = result.mappings().first()
    similar_count = similar['total_projects'] if similar else 0
    similar_avg = similar['avg_contract_value'] if similar else 0
    
    # Feature 2: Agency familiarity
    result = await db.execute(text("""
        SELECT total_projects, on_time_rate
        FROM contractor_agency_experience
        WHERE contractor_name = :contractor_name AND agency_code = :agency_code
    """), {"contractor_name": contractor_name, "agency_code": tender_agency})
    agency_exp = result.mappings().first()
    agency_count = agency_exp['total_projects'] if agency_exp else 0
    agency_ot = agency_exp['on_time_rate'] if agency_exp else 0
    
    # Feature 3: Execution score
    result = await db.execute(text("""
        SELECT execution_score, completion_rate, on_time_rate, total_contracts, total_amount_bdt
        FROM contractor_dna WHERE contractor_id = :contractor_id
    """), {"contractor_id": contractor_id})
    dna = result.mappings().first()
    exec_score = dna['execution_score'] if dna else 50
    comp_rate = dna['completion_rate'] if dna else 0
    ot_rate = dna['on_time_rate'] if dna else 0
    total_contracts = dna['total_contracts'] if dna else 0
    
    # Feature 4: Experience value ratio
    exp_ratio = (similar_avg / tender_value) if tender_value > 0 else 0
    
    # Feature 5: Qualifying projects (similar value range)
    result = await db.execute(text("""
        SELECT COUNT(*) as count
        FROM contractor_execution_history
        WHERE contractor_name = :contractor_name
          AND contract_value_bdt BETWEEN :low AND :high
    """), {"contractor_name": contractor_name, "low": tender_value * 0.5, "high": tender_value * 2.0})
    qual = result.mappings().first()
    qualifying_count = qual['count'] if qual else 0
    
    # Feature 6: Market share (by agency only - award_records_v2 has no work_type column)
    result = await db.execute(text("""
        SELECT COUNT(*) as total FROM award_records_v2
        WHERE agency_code = :agency_code
    """), {"agency_code": tender_agency})
    market_total = result.mappings().first()
    total_market = market_total['total'] if market_total else 1
    
    result = await db.execute(text("""
        SELECT COUNT(*) as contractor_count FROM award_records_v2
        WHERE contractor_name = :contractor_name AND agency_code = :agency_code
    """), {"contractor_name": contractor_name, "agency_code": tender_agency})
    c_awards = result.mappings().first()
    contractor_market = c_awards['contractor_count'] if c_awards else 0
    market_share = (contractor_market / total_market * 100) if total_market > 0 else 0
    
    # Win probability heuristic
    score = 0
    if similar_count > 5: score += 20
    if agency_count > 3: score += 15
    if exec_score > 70: score += 20
    if market_share > 5: score += 15
    if 0.7 < exp_ratio < 1.3: score += 15
    if similar_count > 0 and agency_count > 0: score += 15
    win_prob = min(score, 100)
    
    features_vector = [
        similar_count / 100,
        similar_avg / 1e9,
        agency_count / 100,
        agency_ot or 0,
        exec_score / 100,
        comp_rate,
        ot_rate,
        exp_ratio,
        qualifying_count / 100,
        market_share / 100
    ]
    
    return WinProbabilityFeatures(
        tender_id=tender_id,
        contractor_id=contractor_id,
        contractor_name=contractor_name,
        similar_projects_count=similar_count,
        similar_projects_avg_value=round(similar_avg, 0),
        agency_projects_count=agency_count,
        agency_on_time_rate=round(agency_ot or 0, 1),
        execution_score=round(exec_score, 1),
        completion_rate=round(comp_rate * 100, 1),
        on_time_rate=round(ot_rate * 100, 1),
        experience_value_ratio=round(exp_ratio, 2),
        qualifying_projects_count=qualifying_count,
        market_share_pct=round(market_share, 2),
        win_probability_estimate=win_prob,
        features_vector=[round(f, 4) for f in features_vector]
    )


@router.get("/analytics/win-probability/training-data")
async def training_data(
    limit: int = Query(1000, ge=1, le=10000),
    db: AsyncSession = Depends(get_async_session)
):
    """Export training dataset for win probability ML model.
    
    Returns: List of feature vectors with actual win/loss labels.
    """
    result = await db.execute(text("""
        SELECT 
            ar.tender_id,
            ar.contractor_name,
            ar.amount_bdt,
            ar.agency_code,
            cd.execution_score,
            cd.completion_rate,
            cd.on_time_rate,
            cd.total_contracts,
            c.id as contractor_id
        FROM award_records_v2 ar
        JOIN contractors c ON c.contractor_name = ar.contractor_name
        LEFT JOIN contractor_dna cd ON cd.contractor_id = c.id
        WHERE ar.amount_bdt > 0
        ORDER BY ar.amount_bdt DESC
        LIMIT :limit
    """), {"limit": limit})
    
    rows = result.mappings().all()
    training_set = []
    for row in rows:
        training_set.append({
            "tender_id": row['tender_id'],
            "contractor_id": row['contractor_id'],
            "contractor_name": row['contractor_name'],
            "award_value": row['amount_bdt'],
            "agency": row['agency_code'],
            "execution_score": row['execution_score'],
            "completion_rate": row['completion_rate'],
            "on_time_rate": row['on_time_rate'],
            "total_contracts": row['total_contracts'],
            "label": 1  # Won the tender
        })
    
    return {
        "total_samples": len(training_set),
        "features": [
            "award_value", "execution_score", "completion_rate",
            "on_time_rate", "total_contracts"
        ],
        "data": training_set
    }


# ── 5.3 AI Resume Generator ──────────────────────────────────────────

@router.get("/generate/resume/{contractor_id}")
async def generate_resume(contractor_id: str, db: AsyncSession = Depends(get_async_session)):
    """Generate structured experience resume for bid submission."""
    result = await db.execute(text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})
    c_row = result.mappings().first()
    if not c_row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    contractor_name = c_row['contractor_name']
    
    # DNA profile
    result = await db.execute(text("""
        SELECT total_contracts, total_amount_bdt, avg_award_bdt, completion_rate,
               on_time_rate, execution_score, max_contract_value
        FROM contractor_dna WHERE contractor_id = :contractor_id
    """), {"contractor_id": contractor_id})
    dna = result.mappings().first()
    
    # Agency experience
    result = await db.execute(text("""
        SELECT agency_code, total_projects, completed_projects, total_value_bdt, on_time_rate
        FROM contractor_agency_experience
        WHERE contractor_name = :contractor_name
        ORDER BY total_value_bdt DESC
        LIMIT 10
    """), {"contractor_name": contractor_name})
    agencies = [dict(row) for row in result.mappings().all()]
    
    # Work types
    result = await db.execute(text("""
        SELECT work_type, total_projects, total_value_bdt, avg_contract_value
        FROM contractor_work_similarity
        WHERE contractor_name = :contractor_name
        ORDER BY total_value_bdt DESC
        LIMIT 8
    """), {"contractor_name": contractor_name})
    work_types = [dict(row) for row in result.mappings().all()]
    
    # Key projects
    result = await db.execute(text("""
        SELECT title, contract_value_bdt, agency_code, contract_start_date, contract_end_date, completion_status
        FROM contractor_execution_history
        WHERE contractor_name = :contractor_name AND completion_status ILIKE '%completed%'
        ORDER BY contract_value_bdt DESC
        LIMIT 10
    """), {"contractor_name": contractor_name})
    projects = [dict(row) for row in result.mappings().all()]
    
    # Certificates
    result = await db.execute(text("""
        SELECT certificate_no, agency_code, contract_value_bdt, contract_start_date, contract_end_date
        FROM experience_certificate_registry
        WHERE contractor_name = :contractor_name AND is_valid = TRUE
        LIMIT 10
    """), {"contractor_name": contractor_name})
    certs = [dict(row) for row in result.mappings().all()]
    
    total_projects = dna['total_contracts'] if dna else 0
    total_value = dna['total_amount_bdt'] if dna else 0
    avg_value = dna['avg_award_bdt'] if dna else 0
    max_val = dna['max_contract_value'] if dna else 0
    exec_score = dna['execution_score'] if dna else 0
    comp_rate = dna['completion_rate'] if dna else 0
    ot_rate = dna['on_time_rate'] if dna else 0
    
    executive_summary = (
        f"{contractor_name} is an established contractor with {total_projects} completed projects, "
        f"total executed value of Tk {(total_value/1e6):.1f} million. "
        f"Execution score: {exec_score:.0f}/100. Completion rate: {comp_rate*100:.1f}%. "
        f"On-time delivery rate: {ot_rate*100:.1f}%."
    )
    
    return ContractorResume(
        contractor_name=contractor_name,
        executive_summary=executive_summary,
        total_projects=total_projects,
        completed_projects=int(total_projects * comp_rate) if comp_rate else 0,
        total_value_bdt=total_value,
        avg_project_value=avg_value,
        largest_project=max_val,
        execution_score=exec_score,
        completion_rate=round(comp_rate * 100, 1) if comp_rate else 0,
        on_time_rate=round(ot_rate * 100, 1) if ot_rate else 0,
        agencies_worked=agencies,
        work_experience=work_types,
        key_projects=projects,
        certifications=certs,
        financial_profile={
            "total_executed_value": total_value,
            "avg_project_value": avg_value,
            "largest_project": max_val
        },
        generated_at=datetime.now(timezone.utc).isoformat()
    )


@router.get("/generate/resume/{contractor_id}/docx")
async def generate_resume_docx(contractor_id: str, db: AsyncSession = Depends(get_async_session)):
    """Generate DOCX experience document for bid submission.
    
    Returns: DOCX file download.
    """
    if not DOCX_AVAILABLE:
        raise HTTPException(status_code=500, detail="python-docx library not available")
    
    result = await db.execute(text("SELECT contractor_name FROM contractors WHERE id = :contractor_id"), {"contractor_id": contractor_id})
    c_row = result.mappings().first()
    if not c_row:
        raise HTTPException(status_code=404, detail="Contractor not found")
    contractor_name = c_row['contractor_name']
    
    result = await db.execute(text("SELECT total_contracts, total_amount_bdt, execution_score, completion_rate, on_time_rate, avg_award_bdt, max_contract_value FROM contractor_dna WHERE contractor_id = :contractor_id"), {"contractor_id": contractor_id})
    dna = result.mappings().first()
    
    result = await db.execute(text("SELECT agency_code, total_projects, total_value_bdt FROM contractor_agency_experience WHERE contractor_name = :contractor_name ORDER BY total_value_bdt DESC LIMIT 5"), {"contractor_name": contractor_name})
    agencies = result.mappings().all()
    
    result = await db.execute(text("SELECT title, contract_value_bdt, agency_code, contract_start_date, contract_end_date, completion_status FROM contractor_execution_history WHERE contractor_name = :contractor_name ORDER BY contract_value_bdt DESC LIMIT 8"), {"contractor_name": contractor_name})
    projects = result.mappings().all()
    
    total = dna['total_contracts'] if dna else 0
    value = dna['total_amount_bdt'] if dna else 0
    avg_val = dna['avg_award_bdt'] if dna else 0
    max_val = dna['max_contract_value'] if dna else 0
    exec_score = dna['execution_score'] if dna else 0
    comp_rate = dna['completion_rate'] if dna else 0
    ot_rate = dna['on_time_rate'] if dna else 0
    
    # Build real DOCX
    doc = Document()
    
    # Title
    title = doc.add_heading('Experience Profile', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Contractor name
    p = doc.add_paragraph()
    run = p.add_run(contractor_name)
    run.bold = True
    run.font.size = Pt(16)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph()
    
    # Summary table
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Light Grid Accent 1'
    hdr = table.rows[0].cells
    hdr[0].text = 'Metric'
    hdr[1].text = 'Value'
    for cell in hdr:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
    
    metrics = [
        ('Total Projects', str(total)),
        ('Total Value', f'Tk {value/1e6:.1f} Million'),
        ('Average Project Value', f'Tk {avg_val/1e6:.1f} Million'),
        ('Largest Project', f'Tk {max_val/1e6:.1f} Million'),
        ('Execution Score', f'{exec_score:.0f}/100'),
        ('Completion Rate', f'{comp_rate*100:.1f}%'),
        ('On-Time Rate', f'{ot_rate*100:.1f}%'),
    ]
    for label, val in metrics:
        row = table.add_row().cells
        row[0].text = label
        row[1].text = val
    
    doc.add_paragraph()
    
    # Agency Experience
    doc.add_heading('Agency Experience', level=1)
    if agencies:
        for a in agencies:
            doc.add_paragraph(
                f"{a['agency_code']}: {a['total_projects']} projects, Tk {a['total_value_bdt']/1e6:.1f}M",
                style='List Bullet'
            )
    else:
        doc.add_paragraph('No agency experience data available.')
    
    doc.add_paragraph()
    
    # Key Projects
    doc.add_heading('Key Projects', level=1)
    if projects:
        for p in projects:
            status = p['completion_status'] or 'N/A'
            start = p['contract_start_date'].strftime('%Y-%m-%d') if p['contract_start_date'] else 'N/A'
            end = p['contract_end_date'].strftime('%Y-%m-%d') if p['contract_end_date'] else 'N/A'
            doc.add_paragraph(
                f"{p['title'][:70]} ({p['agency_code']}) - Tk {p['contract_value_bdt']/1e6:.1f}M | Status: {status} | {start} to {end}",
                style='List Bullet'
            )
    else:
        doc.add_paragraph('No project execution data available.')
    
    doc.add_paragraph()
    
    # Footer
    doc.add_paragraph(f"Generated by ProcureFlow on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    
    # Save to bytes
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    
    safe_name = contractor_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_resume.docx"'}
    )
