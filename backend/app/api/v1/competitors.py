"""Competitor Intelligence API routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, text
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import hashlib

from app.db.base import get_async_session
from app.models.competitor import CompetitorProfile, CompetitorAward
from app.models.intelligence import AwardRecordV2
from app.schemas.competitor import CompetitorProfileCreate, CompetitorProfileRead
from app.core.security import get_optional_user, get_current_user
from app.schemas.response_models import CompetitorAwardItem, CompetitorStatsResponse

router = APIRouter(prefix="/competitors", tags=["competitors"])


def _fallback_id(name: str) -> str:
    return hashlib.sha1(name.encode("utf-8", errors="ignore")).hexdigest()[:36]


async def _table_has_rows(db: AsyncSession, table_name: str) -> bool:
    exists = await db.scalar(text("SELECT to_regclass(:table_name)"), {"table_name": f"public.{table_name}"})
    if not exists:
        return False
    # sql-ok: table name supplied by hardcoded callers only
    count = await db.scalar(text(f"SELECT count(*) FROM {table_name}"))
    return bool(count)


async def _award_v2_competitors(
    db: AsyncSession,
    *,
    district: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Aggregate competitor profiles from populated award_records_v2."""
    clauses = ["contractor_name IS NOT NULL", "contractor_name <> ''"]
    params: Dict[str, Any] = {"limit": max(1, min(limit, 500)), "skip": max(0, skip)}
    if district:
        clauses.append("district ILIKE :district")
        params["district"] = f"%{district}%"
    if category:
        clauses.append("agency_code = :category")
        params["category"] = category
    if search:
        clauses.append("contractor_name ILIKE :search")
        params["search"] = f"%{search}%"

    # sql-ok: WHERE fragments from code constants; values bound
    stmt = text(f"""
        SELECT
            contractor_name AS name,
            lower(contractor_name) AS normalized_name,
            max(district) FILTER (WHERE district IS NOT NULL) AS district,
            max(agency_code) FILTER (WHERE agency_code IS NOT NULL) AS category,
            count(*)::int AS total_awards,
            coalesce(sum(amount_bdt), 0)::float AS total_awarded_amount,
            avg(discount_pct)::float AS avg_discount_pct,
            avg(nullif(amount_bdt, 0))::float AS avg_project_size,
            min(award_date) AS first_award_date,
            max(award_date) AS last_award_date,
            jsonb_object_agg(coalesce(district, 'unknown'), district_count) AS active_districts
        FROM (
            SELECT
                contractor_name, district, agency_code, amount_bdt, discount_pct, award_date,
                count(*) OVER (PARTITION BY contractor_name, coalesce(district, 'unknown')) AS district_count
            FROM award_records_v2
            WHERE {" AND ".join(clauses)}
        ) rows
        GROUP BY contractor_name
        ORDER BY coalesce(sum(amount_bdt), 0) DESC
        LIMIT :limit OFFSET :skip
    """)
    result = await db.execute(stmt, params)
    now = datetime.now(timezone.utc)
    rows = []
    for row in result.mappings():
        name = row["name"] or "Unknown Contractor"
        rows.append({
            "id": _fallback_id(name),
            "name": name,
            "normalized_name": row["normalized_name"] or name.lower(),
            "license_number": None,
            "address": None,
            "district": row["district"],
            "division": None,
            "contact_person": None,
            "phone": None,
            "email": None,
            "website": None,
            "entity_type": "Company",
            "category": row["category"],
            "specializations": {},
            "total_awards": row["total_awards"] or 0,
            "total_awarded_amount": float(row["total_awarded_amount"] or 0),
            "avg_discount_pct": float(row["avg_discount_pct"]) if row["avg_discount_pct"] is not None else None,
            "avg_project_size": float(row["avg_project_size"]) if row["avg_project_size"] is not None else None,
            "first_award_date": None,
            "last_award_date": None,
            "active_districts": row["active_districts"] or {},
            "work_types": {},
            "predicted_win_probability": None,
            "predicted_price_range": {},
            "created_at": now,
            "updated_at": now,
        })
    return rows


async def _contractor_dna_competitors(
    db: AsyncSession,
    *,
    district: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """Aggregate competitor profiles from corrected contractor DNA."""
    if await _table_has_rows(db, "contractor_dna_v2"):
        clauses = ["contractor_name IS NOT NULL", "contractor_name <> ''"]
        params: Dict[str, Any] = {"limit": max(1, min(limit, 500)), "skip": max(0, skip)}
        if district:
            clauses.append("zone_affinity::jsonb ? :district")
            params["district"] = district
        if category:
            clauses.append("agency_affinity::jsonb ? :category")
            params["category"] = category
        if search:
            clauses.append("contractor_name ILIKE :search")
            params["search"] = f"%{search}%"

        # sql-ok: WHERE fragments from code constants; values bound
        result = await db.execute(text(f"""
            SELECT
                contractor_id AS id,
                contractor_name AS name,
                lower(contractor_name) AS normalized_name,
                total_wins::int AS total_awards,
                total_award_amount_bdt::float AS total_awarded_amount,
                avg_discount::float AS avg_discount_pct,
                avg_award_amount_bdt::float AS avg_project_size,
                agency_affinity,
                zone_affinity,
                win_rate,
                avg_rank,
                responsive_rate,
                slt_rate,
                health_score
            FROM contractor_dna_v2
            WHERE {" AND ".join(clauses)}
            ORDER BY total_award_amount_bdt DESC, total_wins DESC
            LIMIT :limit OFFSET :skip
        """), params)
        now = datetime.now(timezone.utc)
        rows = []
        for row in result.mappings():
            name = row["name"] or "Unknown Contractor"
            active_districts = dict(row.get("zone_affinity") or {})
            category_map = dict(row.get("agency_affinity") or {})
            rows.append({
                "id": row["id"] or _fallback_id(name),
                "name": name,
                "normalized_name": row["normalized_name"] or name.lower(),
                "license_number": None,
                "address": None,
                "district": next(iter(active_districts), None),
                "division": None,
                "contact_person": None,
                "phone": None,
                "email": None,
                "website": None,
                "entity_type": "Company",
                "category": next(iter(category_map), None),
                "specializations": {
                    "win_rate": float(row.get("win_rate") or 0),
                    "avg_rank": float(row.get("avg_rank") or 0),
                    "responsive_rate": float(row.get("responsive_rate") or 0),
                    "slt_rate": float(row.get("slt_rate") or 0),
                    "health_score": float(row.get("health_score") or 0),
                },
                "total_awards": row["total_awards"] or 0,
                "total_awarded_amount": float(row["total_awarded_amount"] or 0),
                "avg_discount_pct": float(row["avg_discount_pct"]) if row["avg_discount_pct"] is not None else None,
                "avg_project_size": float(row["avg_project_size"]) if row["avg_project_size"] is not None else None,
                "first_award_date": None,
                "last_award_date": None,
                "active_districts": active_districts,
                "work_types": {},
                "predicted_win_probability": None,
                "predicted_price_range": {},
                "created_at": now,
                "updated_at": now,
            })
        return rows

    clauses = ["c.contractor_name IS NOT NULL", "c.contractor_name <> ''"]
    params: Dict[str, Any] = {"limit": max(1, min(limit, 500)), "skip": max(0, skip)}
    if district:
        clauses.append("cd.preferred_zone ILIKE :district")
        params["district"] = f"%{district}%"
    if category:
        clauses.append("cd.preferred_agency = :category")
        params["category"] = category
    if search:
        clauses.append("c.contractor_name ILIKE :search")
        params["search"] = f"%{search}%"

    # sql-ok: WHERE fragments from code constants; values bound
    result = await db.execute(text(f"""
        SELECT
            c.id,
            c.contractor_name AS name,
            lower(c.contractor_name) AS normalized_name,
            cd.preferred_zone AS district,
            cd.preferred_agency AS category,
            cd.total_contracts::int AS total_awards,
            coalesce(cd.total_amount_bdt, 0)::float AS total_awarded_amount,
            cd.avg_discount_pct::float AS avg_discount_pct,
            cd.avg_award_bdt::float AS avg_project_size,
            cd.first_award_date,
            cd.last_award_date
        FROM contractor_dna cd
        JOIN contractors c ON c.id = cd.contractor_id
        WHERE {" AND ".join(clauses)}
        ORDER BY coalesce(cd.total_amount_bdt, 0) DESC
        LIMIT :limit OFFSET :skip
    """), params)
    now = datetime.now(timezone.utc)
    rows = []
    for row in result.mappings():
        name = row["name"] or "Unknown Contractor"
        rows.append({
            "id": row["id"] or _fallback_id(name),
            "name": name,
            "normalized_name": row["normalized_name"] or name.lower(),
            "license_number": None,
            "address": None,
            "district": row["district"],
            "division": None,
            "contact_person": None,
            "phone": None,
            "email": None,
            "website": None,
            "entity_type": "Company",
            "category": row["category"],
            "specializations": {},
            "total_awards": row["total_awards"] or 0,
            "total_awarded_amount": float(row["total_awarded_amount"] or 0),
            "avg_discount_pct": float(row["avg_discount_pct"]) if row["avg_discount_pct"] is not None else None,
            "avg_project_size": float(row["avg_project_size"]) if row["avg_project_size"] is not None else None,
            "first_award_date": None,
            "last_award_date": None,
            "active_districts": {},
            "work_types": {},
            "predicted_win_probability": None,
            "predicted_price_range": {},
            "created_at": now,
            "updated_at": now,
        })
    return rows


@router.post("/", response_model=CompetitorProfileRead)
async def create_competitor(
    competitor: CompetitorProfileCreate,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    """Create a new competitor profile"""
    # Normalize name for searching
    normalized = competitor.name.lower().strip()
    db_competitor = CompetitorProfile(
        **competitor.model_dump(),
        normalized_name=normalized,
    )
    db.add(db_competitor)
    await db.commit()
    await db.refresh(db_competitor)
    return db_competitor


@router.get("/", response_model=List[CompetitorProfileRead])
async def list_competitors(
    district: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """List competitor profiles with filters"""
    dna_rows = await _contractor_dna_competitors(
        db, district=district, category=category, search=search, skip=skip, limit=limit
    )
    if dna_rows:
        return dna_rows

    stmt = select(CompetitorProfile)
    
    if district:
        stmt = stmt.where(CompetitorProfile.district.ilike(f"%{district}%"))
    if category:
        stmt = stmt.where(CompetitorProfile.category == category)
    if search:
        stmt = stmt.where(CompetitorProfile.normalized_name.ilike(f"%{search.lower()}%"))
    
    stmt = stmt.order_by(desc(CompetitorProfile.total_awarded_amount)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    if rows:
        return rows
    return await _award_v2_competitors(
        db, district=district, category=category, search=search, skip=skip, limit=limit
    )


@router.get("/stats", response_model=CompetitorStatsResponse)
async def get_competitor_stats(
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """Get competitor statistics"""
    if await _table_has_rows(db, "contractor_dna_v2"):
        dna_total = await db.execute(text("""
            SELECT
                count(*)::int AS total_competitors,
                coalesce(sum(total_award_amount_bdt), 0)::float AS total_awarded_amount
            FROM contractor_dna_v2
        """))
        dna_row = dna_total.mappings().first() or {}
        top_agencies = await db.execute(text("""
            SELECT key AS category, count(*)::int AS count, coalesce(sum(total_award_amount_bdt), 0)::float AS total_amount
            FROM contractor_dna_v2, LATERAL jsonb_object_keys(agency_affinity::jsonb) AS key
            GROUP BY key
            ORDER BY total_amount DESC
            LIMIT 10
        """))
        top_districts = await db.execute(text("""
            SELECT key AS district, count(*)::int AS count, coalesce(sum(total_award_amount_bdt), 0)::float AS total_amount
            FROM contractor_dna_v2, LATERAL jsonb_object_keys(zone_affinity::jsonb) AS key
            GROUP BY key
            ORDER BY total_amount DESC
            LIMIT 10
        """))
        return {
            "total_competitors": dna_row.get("total_competitors", 0),
            "total_awarded_amount": float(dna_row.get("total_awarded_amount") or 0),
            "source": "contractor_dna_v2",
            "by_category": [
                {"category": r[0], "count": r[1], "total_amount": float(r[2] or 0)}
                for r in top_agencies
            ],
            "by_district": [
                {"district": r[0], "count": r[1], "total_amount": float(r[2] or 0)}
                for r in top_districts
            ],
        }

    dna_total = await db.execute(text("""
        SELECT
            count(*)::int AS total_competitors,
            coalesce(sum(total_amount_bdt), 0)::float AS total_awarded_amount
        FROM contractor_dna
    """))
    dna_row = dna_total.mappings().first() or {}
    if int(dna_row.get("total_competitors") or 0) > 0:
        top_agencies = await db.execute(text("""
            SELECT coalesce(preferred_agency, 'unknown') AS category,
                   count(*)::int AS count,
                   coalesce(sum(total_amount_bdt), 0)::float AS total_amount
            FROM contractor_dna
            GROUP BY coalesce(preferred_agency, 'unknown')
            ORDER BY total_amount DESC
            LIMIT 10
        """))
        top_districts = await db.execute(text("""
            SELECT coalesce(preferred_zone, 'unknown') AS district,
                   count(*)::int AS count,
                   coalesce(sum(total_amount_bdt), 0)::float AS total_amount
            FROM contractor_dna
            GROUP BY coalesce(preferred_zone, 'unknown')
            ORDER BY total_amount DESC
            LIMIT 10
        """))
        return {
            "total_competitors": dna_row.get("total_competitors", 0),
            "total_awarded_amount": float(dna_row.get("total_awarded_amount") or 0),
            "source": "contractor_dna",
            "by_category": [
                {"category": r[0], "count": r[1], "total_amount": float(r[2] or 0)}
                for r in top_agencies
            ],
            "by_district": [
                {"district": r[0], "count": r[1], "total_amount": float(r[2] or 0)}
                for r in top_districts
            ],
        }

    total = await db.scalar(select(func.count(CompetitorProfile.id)))
    total_amount = await db.scalar(select(func.sum(CompetitorProfile.total_awarded_amount)))
    if not total:
        fallback = await db.execute(text("""
            SELECT
                count(DISTINCT contractor_name)::int AS total_competitors,
                coalesce(sum(amount_bdt), 0)::float AS total_awarded_amount
            FROM award_records_v2
            WHERE contractor_name IS NOT NULL AND contractor_name <> ''
        """))
        top_agencies = await db.execute(text("""
            SELECT coalesce(agency_code, 'unknown') AS category,
                   count(DISTINCT contractor_name)::int AS count,
                   coalesce(sum(amount_bdt), 0)::float AS total_amount
            FROM award_records_v2
            WHERE contractor_name IS NOT NULL AND contractor_name <> ''
            GROUP BY coalesce(agency_code, 'unknown')
            ORDER BY total_amount DESC
            LIMIT 10
        """))
        top_districts = await db.execute(text("""
            SELECT coalesce(district, 'unknown') AS district,
                   count(DISTINCT contractor_name)::int AS count,
                   coalesce(sum(amount_bdt), 0)::float AS total_amount
            FROM award_records_v2
            WHERE contractor_name IS NOT NULL AND contractor_name <> ''
            GROUP BY coalesce(district, 'unknown')
            ORDER BY total_amount DESC
            LIMIT 10
        """))
        row = fallback.mappings().first() or {}
        return {
            "total_competitors": row.get("total_competitors", 0),
            "total_awarded_amount": float(row.get("total_awarded_amount") or 0),
            "source": "award_records_v2",
            "by_category": [
                {"category": r[0], "count": r[1], "total_amount": float(r[2] or 0)}
                for r in top_agencies
            ],
            "by_district": [
                {"district": r[0], "count": r[1], "total_amount": float(r[2] or 0)}
                for r in top_districts
            ],
        }
    
    # By category
    by_category = await db.execute(
        select(CompetitorProfile.category, func.count(CompetitorProfile.id), func.sum(CompetitorProfile.total_awarded_amount))
        .group_by(CompetitorProfile.category)
        .order_by(func.sum(CompetitorProfile.total_awarded_amount).desc())
    )
    
    # By district
    by_district = await db.execute(
        select(CompetitorProfile.district, func.count(CompetitorProfile.id), func.sum(CompetitorProfile.total_awarded_amount))
        .group_by(CompetitorProfile.district)
        .order_by(func.sum(CompetitorProfile.total_awarded_amount).desc())
        .limit(10)
    )
    
    return {
        "total_competitors": total or 0,
        "total_awarded_amount": float(total_amount) if total_amount else 0,
        "by_category": [
            {"category": r[0], "count": r[1], "total_amount": float(r[2])}
            for r in by_category if r[0]
        ],
        "by_district": [
            {"district": r[0], "count": r[1], "total_amount": float(r[2])}
            for r in by_district if r[0]
        ],
    }


@router.get("/analysis/{tender_id}")
async def get_competitor_analysis(
    tender_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """Get competitor analysis for a specific tender — returns CompetitorAnalysis shape."""
    from app.models.award import Award
    from datetime import datetime, timezone
    top = (await db.execute(
        select(AwardRecordV2.contractor_name, func.count().label("cnt"))
        .where(AwardRecordV2.tender_id == tender_id)
        .group_by(AwardRecordV2.contractor_name)
        .order_by(desc(func.count()))
        .limit(5)
    )).all()
    if not top:
        return None
    competitors = []
    for row in top:
        name = row[0] or "Unknown"
        competitors.append({
            "competitor_id": _fallback_id(name),
            "name": name,
            "win_rate": 0,
            "total_bids": row[1],
            "total_wins": 0,
            "avg_discount": 0,
            "specialties": [],
            "agencies": [],
            "recent_activity": [],
        })
    return {
        "tender_id": tender_id,
        "competitors": competitors,
        "market_position": f"Competing with {len(competitors)} other contractors",
        "threat_level": "high" if len(competitors) >= 5 else "medium" if len(competitors) >= 3 else "low",
        "recommendations": [
            "Focus on competitive pricing strategy",
            "Highlight unique value proposition",
        ],
    }


@router.get("/{competitor_id}", response_model=CompetitorProfileRead)
async def get_competitor(
    competitor_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """Get competitor by ID"""
    stmt = select(CompetitorProfile).where(CompetitorProfile.id == competitor_id)
    result = await db.execute(stmt)
    competitor = result.scalar_one_or_none()
    if not competitor:
        rows = await _award_v2_competitors(db, search=competitor_id, limit=1)
        if rows:
            return rows[0]
        raise HTTPException(status_code=404, detail="Competitor not found")
    return competitor


@router.get("/{competitor_id}/awards", response_model=List[CompetitorAwardItem])
async def get_competitor_awards(
    competitor_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    """Get awards for a specific competitor"""
    from app.models.award import Award
    
    stmt = select(AwardRecord).join(
        CompetitorAward, CompetitorAward.award_id == AwardRecord.id
    ).where(CompetitorAward.competitor_id == competitor_id)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    if rows:
        return rows
    awards = await db.execute(text("""
        SELECT id, tender_id, package_no, title, contractor_name, amount_bdt,
               estimated_amount_bdt, award_date, agency_code, district, procuring_entity
        FROM award_records_v2
        WHERE contractor_name ILIKE :name
        ORDER BY award_date DESC NULLS LAST
        LIMIT 200
    """), {"name": f"%{competitor_id}%"})
    return [dict(r) for r in awards.mappings()]
