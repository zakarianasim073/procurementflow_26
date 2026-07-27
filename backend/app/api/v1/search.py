"""Search API — unified full-text search over tenders, awards, contractors."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_optional_user
from app.db.base import get_async_session
from app.schemas.response_models import GlobalSearchResponse, SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/tenders", response_model=SearchResponse)
async def search_tenders(
    q: str = Query("", max_length=200),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    agency: str | None = Query(None, max_length=50),
    scope: str = Query("live", pattern="^(live|all)$"),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    return await SearchService.search_tenders(
        db, q, agency=agency, limit=limit, offset=offset, scope=scope
    )


@router.get("/awards", response_model=SearchResponse)
async def search_awards(
    q: str = Query("", max_length=200),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    district: str | None = Query(None, max_length=100),
    contractor: str | None = Query(None, max_length=200),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    return await SearchService.search_awards(
        db, q, district=district, contractor=contractor, limit=limit, offset=offset
    )


@router.get("/contractors", response_model=SearchResponse)
async def search_contractors(
    q: str = Query("", max_length=200),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    return await SearchService.search_contractors(db, q, limit=limit, offset=offset)


@router.get("/global", response_model=GlobalSearchResponse)
async def search_global(
    q: str = Query(..., min_length=2, max_length=200),
    limit_per_type: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    return await SearchService.search_global(db, q, limit_per_type=limit_per_type)
