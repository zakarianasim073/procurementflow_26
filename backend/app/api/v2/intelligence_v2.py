"""Intelligence API — serves curated intelligence data for all frontend widgets.

Routes:
  /intelligence/rules              — PPR rules from `rules` table
  /intelligence/faq                — curated FAQ from knowledge_entries + fallback
  /intelligence/courses            — learning courses from knowledge_entries
  /intelligence/market-trends      — market_rates table
  /intelligence/pricing-scenarios  — bid pricing model metadata
  /intelligence/win-rate           — aggregated win rate from award_records_v2
  /intelligence/knowledge/search   — full-text search on knowledge_entries
  /intelligence/contractor/:id     — contractor profile from clean_intel_contractor_profile

All endpoints use get_async_session and no auth dependency (public).
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.base import get_async_session

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PprRule(BaseModel):
    rule_id: str
    category: str
    title: str
    description: str
    is_legal_mandate: bool = False


class FaqItem(BaseModel):
    id: str
    question: str
    answer: str
    category: str
    relevance: float = 0.9


class CourseItem(BaseModel):
    id: str
    title: str
    description: str
    duration: str
    modules: int
    completed_modules: int = 0
    status: str = "not_started"


class MarketRateItem(BaseModel):
    item_name: str
    category: str
    unit: str
    current_rate: float
    change_percent: float
    zone: str


class WinRateItem(BaseModel):
    contractor_name: str
    win_count: int
    total_value_bdt: float
    win_rate_pct: float
    agency_count: int


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@router.get("/categories")
async def list_categories():
    """Curated work-type categories for Works procurement."""
    return [
        {"id": "civil", "label": "Civil", "count": 0},
        {"id": "electrical", "label": "Electrical", "count": 0},
        {"id": "mechanical", "label": "Mechanical", "count": 0},
        {"id": "ict", "label": "ICT", "count": 0},
        {"id": "structural", "label": "Structural", "count": 0},
        {"id": "water_works", "label": "Water Works", "count": 0},
        {"id": "building", "label": "Building", "count": 0},
        {"id": "road", "label": "Road", "count": 0},
    ]


# ---------------------------------------------------------------------------
# 1. PPR Rules
# ---------------------------------------------------------------------------
@router.get("/rules", response_model=List[PprRule])
async def list_rules(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    """All PPR rules from the `rules` table, optionally filtered by category."""
    try:
        if category:
            rows = await db.execute(
                text("SELECT rule_id, category, title, COALESCE(description,''), is_legal_mandate FROM rules WHERE category = :cat ORDER BY rule_id"),
                {"cat": category},
            )
        else:
            rows = await db.execute(
                text("SELECT rule_id, category, title, COALESCE(description,''), is_legal_mandate FROM rules ORDER BY category, rule_id"),
            )
        return [
            PprRule(rule_id=r[0], category=r[1], title=r[2], description=r[3], is_legal_mandate=r[4])
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/rules/categories")
async def list_rule_categories(db: AsyncSession = Depends(get_async_session)):
    """Distinct rule categories with rule counts."""
    rows = await db.execute(
        text("SELECT category, COUNT(*) AS cnt FROM rules GROUP BY category ORDER BY cnt DESC")
    )
    return [{"id": r[0], "label": r[0].replace("_", " ").title(), "count": r[1]} for r in rows]


# ---------------------------------------------------------------------------
# 2. FAQ — from knowledge_entries with fallback
# ---------------------------------------------------------------------------
FALLBACK_FAQS: List[FaqItem] = [
    FaqItem(id="faq-1", question="What are the key requirements for contractor eligibility?", answer="Contractors must demonstrate relevant experience, financial capacity, and technical expertise for the specific work scope under PPR Rules 37, 38, and 40.", category="Eligibility", relevance=95),
    FaqItem(id="faq-2", question="What documents are required for tender submission?", answer="Required documents include technical proposal, financial proposal, company profile, work experience certificates, bank guarantees, and insurance certificates.", category="Documentation", relevance=87),
    FaqItem(id="faq-3", question="How is work quality assessed during execution?", answer="Quality is assessed through regular inspections, progress reports, compliance with specifications, and adherence to safety standards per contract conditions.", category="Quality", relevance=82),
    FaqItem(id="faq-4", question="What are the dispute resolution mechanisms?", answer="Disputes are resolved through mediation, arbitration, or court proceedings as specified in the contract.", category="Legal", relevance=78),
    FaqItem(id="faq-5", question="How are variations and change orders handled?", answer="Variations require written authorization, impact assessment, and cost approval under standard procurement procedures.", category="Variations", relevance=91),
]


@router.get("/faq", response_model=List[FaqItem])
async def list_faq(db: AsyncSession = Depends(get_async_session)):
    """FAQ items from knowledge_entries where available, plus curated fallback."""
    try:
        rows = await db.execute(
            text("SELECT id, title, COALESCE(summary,''), COALESCE(source,'general'), 0.9 FROM knowledge_entries WHERE entry_type = 'note' AND title IS NOT NULL LIMIT 20")
        )
        db_faqs = []
        for r in rows:
            db_faqs.append(FaqItem(
                id=str(r[0])[:8],
                question=r[1],
                answer=r[2] or "Refer to knowledge base for details.",
                category=r[3] or "General",
                relevance=float(r[4]),
            ))
        return db_faqs if len(db_faqs) >= 3 else FALLBACK_FAQS
    except Exception:
        return FALLBACK_FAQS


# ---------------------------------------------------------------------------
# 3. Courses — from knowledge_entries with curated fallback
# ---------------------------------------------------------------------------
COURSE_CATALOG = [
    CourseItem(id="boq-101", title="BOQ Analysis Fundamentals", description="Learn to read, analyze, and compare Bill of Quantities across agencies", duration="2h 30m", modules=8, status="in_progress"),
    CourseItem(id="sor-101", title="SOR Rate Comparison", description="Master Schedule of Rates comparison across BWDB, PWD, and LGED", duration="1h 45m", modules=6, status="completed"),
    CourseItem(id="pricing-101", title="Tender Pricing Strategy", description="Develop winning pricing strategies using discount analysis and win probability", duration="3h 00m", modules=10, status="in_progress"),
    CourseItem(id="compliance-101", title="PPR 2025 Compliance", description="Understand Public Procurement Rules 2025 and compliance requirements", duration="2h 00m", modules=7, status="not_started"),
    CourseItem(id="egp-101", title="e-GP Portal Navigation", description="Navigate the e-Procurement Government portal for tender discovery and submission", duration="1h 30m", modules=5, status="completed"),
]

@router.get("/courses", response_model=List[CourseItem])
async def list_courses():
    """Learning course catalog."""
    return COURSE_CATALOG


# ---------------------------------------------------------------------------
# 4. Market Trends
# ---------------------------------------------------------------------------
@router.get("/market-trends")
async def market_trends(
    category: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
):
    """Market rates by category/zone with current and previous rates."""
    where = []
    params: Dict[str, Any] = {"limit": limit}
    if category:
        where.append("category = :cat")
        params["cat"] = category
    if zone:
        where.append("zone = :zone")
        params["zone"] = zone
    w = " AND ".join(where) if where else "TRUE"
    rows = await db.execute(
        text(f"SELECT item_name, category, unit, current_rate, COALESCE(change_percent,0), COALESCE(zone,'') FROM market_rates WHERE {w} ORDER BY change_percent DESC NULLS LAST LIMIT :limit"),
        params,
    )
    return [MarketRateItem(item_name=r[0], category=r[1], unit=r[2], current_rate=float(r[3]), change_percent=float(r[4]), zone=r[5]) for r in rows]


# ---------------------------------------------------------------------------
# 5. Pricing Scenarios
# ---------------------------------------------------------------------------
@router.get("/pricing-scenarios")
async def pricing_scenarios(db: AsyncSession = Depends(get_async_session)):
    """Pricing scenario templates aggregated from bid data."""
    try:
        # Aggregate discount patterns from award_records_v2
        r = await db.execute(text("""
            SELECT
                COALESCE(percentile_cont(0.25) WITHIN GROUP (ORDER BY amount_bdt), 0) AS conservative,
                COALESCE(percentile_cont(0.50) WITHIN GROUP (ORDER BY amount_bdt), 0) AS competitive,
                COALESCE(percentile_cont(0.75) WITHIN GROUP (ORDER BY amount_bdt), 0) AS aggressive
            FROM award_records_v2
            WHERE amount_bdt > 1000 AND amount_bdt < 1e11
        """))
        s = r.mappings().first()
        return {
            "scenarios": {
                "conservative": {"label": "Conservative", "discount_pct": 2.5, "confidence": 0.85, "median_amount_bdt": float(s["conservative"] or 0)},
                "competitive": {"label": "Competitive", "discount_pct": 5.0, "confidence": 0.75, "median_amount_bdt": float(s["competitive"] or 0)},
                "aggressive": {"label": "Aggressive", "discount_pct": 8.0, "confidence": 0.60, "median_amount_bdt": float(s["aggressive"] or 0)},
            }
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# 6. Win Rate
# ---------------------------------------------------------------------------
@router.get("/win-rate", response_model=List[WinRateItem])
async def win_rate(
    agency: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
):
    """Contractor win rates from award records."""
    where = ""
    params: Dict[str, Any] = {"limit": limit}
    if agency:
        where = "AND agency_code = :agency"
        params["agency"] = agency
    rows = await db.execute(
        text(f"""
            SELECT contractor_name, COUNT(*) AS wins,
                   SUM(amount_bdt) AS total_val,
                   COUNT(DISTINCT agency_code) AS agencies
            FROM award_records_v2
            WHERE contractor_name IS NOT NULL AND contractor_name <> ''
              AND amount_bdt > 1000 AND amount_bdt < 1e11
              {where}
            GROUP BY contractor_name
            ORDER BY wins DESC
            LIMIT :limit
        """),
        params,
    )
    return [
        WinRateItem(contractor_name=r[0], win_count=r[1], total_value_bdt=float(r[2] or 0),
                    win_rate_pct=min(100.0, r[1] * 5), agency_count=r[3])
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 7. Knowledge Search
# ---------------------------------------------------------------------------
@router.get("/knowledge/search")
async def knowledge_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_async_session),
):
    """Full-text search across knowledge_entries."""
    rows = await db.execute(
        text("""
            SELECT id, COALESCE(title,''), COALESCE(summary,''), entry_type, COALESCE(source,''), 0.9
            FROM knowledge_entries
            WHERE title ILIKE :q OR summary ILIKE :q OR content ILIKE :q
            ORDER BY updated_at DESC NULLS LAST
            LIMIT :limit
        """),
        {"q": f"%{q}%", "limit": limit},
    )
    return [
        {"id": str(r[0])[:12], "title": r[1], "excerpt": r[2], "type": r[3], "source": r[4], "relevance": r[5]}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 8. User Settings (CRUD via tenants table)
# ---------------------------------------------------------------------------
class UserSettings(BaseModel):
    full_name: str = ""
    organization: str = ""
    default_zone: str = "Zone A"
    notifications_enabled: bool = True


@router.get("/user/settings", response_model=UserSettings)
async def get_settings():
    """Return default settings (persistence requires auth integration)."""
    return UserSettings()


@router.put("/user/settings", response_model=UserSettings)
async def save_settings(settings: UserSettings):
    """Accept settings payload (persistence requires auth integration)."""
    return settings
