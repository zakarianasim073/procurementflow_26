"""Serve the clean_intel_<name> intelligence tables to the frontend.

Tables loaded by scripts/import_clean_intelligence.py, each row a JSONB
record plus a promoted key_id. This exposes them generically: a catalogue,
a paginated list per dataset, and a single-record lookup by key. Table names
are validated against the actual clean_intel_ set so the JSONB path cannot be
used for injection.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.base import get_async_session

router = APIRouter(prefix="/clean-intel", tags=["clean-intel"])


async def _datasets(db: AsyncSession, works_only: bool = False) -> List[str]:
    suffix = " AND tablename LIKE 'clean_intel_works_%'" if works_only else ""
    rows = await db.execute(text(
        "SELECT tablename FROM pg_tables "
        f"WHERE tablename LIKE 'clean_intel_%'{suffix} ORDER BY 1"))
    return [r[0].removeprefix("clean_intel_") for r in rows]


async def _resolve(db: AsyncSession, dataset: str) -> str:
    table = "clean_intel_" + dataset.lower().replace("-", "_")
    if table not in {"clean_intel_" + d for d in await _datasets(db)}:
        raise HTTPException(404, f"unknown dataset '{dataset}'")
    return table


@router.get("/catalogue")
async def catalogue(
    works_only: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[Dict[str, Any]]:
    """Every dataset with its row count."""
    out = []
    for d in await _datasets(db, works_only=works_only):
        n = await db.scalar(text(f"SELECT count(*) FROM clean_intel_{d}"))
        out.append({"dataset": d, "rows": n})
    return out


@router.get("/{dataset}")
async def list_dataset(
    dataset: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None, description="substring match on key_id"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Paginated rows of one dataset; each row is the source JSONB record."""
    table = await _resolve(db, dataset)
    where = "WHERE key_id ILIKE :q" if q else ""
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    if q:
        params["q"] = f"%{q}%"
    total = await db.scalar(text(f"SELECT count(*) FROM {table} {where}"), params)
    rows = await db.execute(text(
        f"SELECT key_id, data FROM {table} {where} ORDER BY id LIMIT :limit OFFSET :offset"), params)
    import json
    return {
        "dataset": dataset,
        "total": total,
        "rows": [{"key_id": r[0], **(r[1] if isinstance(r[1], dict) else json.loads(r[1]))}
                 for r in rows],
    }


@router.get("/{dataset}/{key}")
async def get_record(
    dataset: str,
    key: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Single record by its promoted key_id (exact match)."""
    table = await _resolve(db, dataset)
    row = await db.execute(text(
        f"SELECT key_id, data FROM {table} WHERE key_id = :k LIMIT 1"), {"k": key})
    r = row.first()
    if not r:
        raise HTTPException(404, f"no record with key '{key}' in {dataset}")
    import json
    return {"key_id": r[0], **(r[1] if isinstance(r[1], dict) else json.loads(r[1]))}
