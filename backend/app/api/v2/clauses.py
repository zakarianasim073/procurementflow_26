from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from pydantic import BaseModel
from datetime import datetime

from app.db.base import get_async_session
from app.models.regulatory import Clause as DBClause

router = APIRouter(tags=["clauses"])


class Precedent(BaseModel):
    case_name: str
    year: int
    court: str
    summary: str


class ClauseTreeNode(BaseModel):
    id: str
    label: str
    children: List['ClauseTreeNode'] = []
    clause_count: int = 0


class ClauseTag(BaseModel):
    id: str
    label: str
    count: int


class Clause(BaseModel):
    id: str
    rule_id: Optional[str] = None
    title: str
    official_text: str
    plain_english: Optional[str] = None
    common_mistakes: List[dict] = []
    precedents: List[Precedent] = []
    related_clauses: List[str] = []
    faq: List[dict] = []
    tags: List[str] = []
    severity: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClauseListResponse(BaseModel):
    items: List[Clause]
    total: int
    page: int
    page_size: int
    has_more: bool


class RelatedClause(BaseModel):
    clause_id: str
    rule_id: str
    title: str
    relationship_type: str  # requires, contradicts, overrides, clarifies


@router.get("/clauses", response_model=ClauseListResponse)
async def list_clauses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session)
):
    """List all clauses with pagination and search."""
    stmt = select(DBClause)

    # Apply search filter
    if search:
        stmt = stmt.where(
            or_(
                func.lower(DBClause.title).contains(search.lower()),
                func.lower(DBClause.full_text).contains(search.lower()),
                func.lower(DBClause.clause_ref).contains(search.lower())
            )
        )

    # Count total
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()

    # Paginate
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()

    return ClauseListResponse(
        items=[_db_clause_to_api(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total
    )


@router.get("/clauses/tree", response_model=ClauseTreeNode)
async def get_clause_tree(db: AsyncSession = Depends(get_async_session)):
    """Get hierarchical clause tree grouped by rule prefix."""
    all_clauses = (await db.execute(select(DBClause).limit(200))).scalars().all()
    groups: dict[str, list] = {}
    for c in all_clauses:
        prefix = (c.clause_ref or "other").split()[0] if c.clause_ref else "other"
        groups.setdefault(prefix, []).append(c)
    children = [
        ClauseTreeNode(id=prefix, label=prefix.replace("_", " ").title(), clause_count=len(items))
        for prefix, items in sorted(groups.items())
    ]
    return ClauseTreeNode(id="root", label="All Clauses", children=children, clause_count=len(all_clauses))


@router.get("/clauses/tags", response_model=List[ClauseTag])
async def get_clause_tags(db: AsyncSession = Depends(get_async_session)):
    """Get distinct tags from clause ref prefixes."""
    all_clauses = (await db.execute(select(DBClause).limit(500))).scalars().all()
    counts: dict[str, int] = {}
    for c in all_clauses:
        prefix = (c.clause_ref or "other").split()[0] if c.clause_ref else "other"
        counts[prefix] = counts.get(prefix, 0) + 1
    return [ClauseTag(id=k, label=k.replace("_", " ").title(), count=v) for k, v in sorted(counts.items())]


# NOTE: /clauses/search MUST be declared before /clauses/{clause_id},
# otherwise FastAPI matches "search" as a clause_id path param.
@router.get("/clauses/search", response_model=List[Clause])
async def search_clauses(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_session)
):
    """Full-text search across clause text, titles, and refs."""
    stmt = select(DBClause).where(
        or_(
            func.lower(DBClause.title).contains(q.lower()),
            func.lower(DBClause.full_text).contains(q.lower()),
            func.lower(DBClause.clause_ref).contains(q.lower())
        )
    ).limit(limit)
    result = await db.execute(stmt)
    return [_db_clause_to_api(c) for c in result.scalars().all()]


@router.get("/clauses/{clause_id}", response_model=Clause)
async def get_clause(clause_id: str, db: AsyncSession = Depends(get_async_session)):
    """Get full details of a specific clause."""
    result = await db.execute(select(DBClause).where(DBClause.id == clause_id))
    clause = result.scalars().first()
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")
    return _db_clause_to_api(clause)


@router.get("/clauses/{clause_id}/related", response_model=List[RelatedClause])
async def get_related_clauses(clause_id: str, db: AsyncSession = Depends(get_async_session)):
    """Get clauses related to this one by same rule category."""
    try:
        result = await db.execute(
            select(DBClause).where(DBClause.id == clause_id)
        )
        clause = result.scalar_one_or_none()
        if not clause:
            raise HTTPException(status_code=404, detail="Clause not found")

        rule_prefix = clause.clause_ref.split()[0] if clause.clause_ref else None
        if not rule_prefix:
            return []

        related = (await db.execute(
            select(DBClause)
            .where(
                DBClause.clause_ref.ilike(f"{rule_prefix}%"),
                DBClause.id != clause_id,
            )
            .limit(5)
        )).scalars().all()

        return [_db_clause_to_api(c) for c in related]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _db_clause_to_api(db_clause: DBClause) -> Clause:
    """Convert DB Clause model to API Clause response."""
    return Clause(
        id=db_clause.id,
        rule_id=db_clause.clause_ref.split()[0] if db_clause.clause_ref else None,
        title=db_clause.title or "Untitled",
        official_text=db_clause.full_text or "",
        plain_english=db_clause.full_text or "",
        common_mistakes=[],
        precedents=[],
        related_clauses=[],
        faq=[],
        tags=[db_clause.clause_ref.split()[0] if db_clause.clause_ref else "clause"],
        severity="medium",
        created_at=db_clause.created_at,
        updated_at=db_clause.created_at
    )
