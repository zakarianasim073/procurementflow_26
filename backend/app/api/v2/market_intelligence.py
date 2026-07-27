"""Market intelligence endpoints for the Knowledge Platform.

These replace the analytics-warehouse routes, which report zero value for
every aggregate (``analytics/market-overview`` returns total_value_bdt 0.0,
``contractors-performance`` returns an empty list, ``category-trends`` 500s).

Two tables are used, each for what it actually holds:

``award_records_v2`` is the award record — 1,104,451 rows, of which 1,065,354
carry a usable amount, across 231 agencies and 66,697 contractors. Volume,
value, agency behaviour and contractor standings all come from here.

``procurement_lifecycle`` is smaller (657,975 rows) but is the only place an
estimate sits alongside an award, so NPPI is computed there.
``award_records_v2`` has an ``estimated_amount_bdt`` column but only 265 rows
populate it, which is far too thin to aggregate.

Three data-quality rules apply throughout:

* Amounts below 10 are crore-denominated at source, so a raw 0.474 means
  0.474 Cr. They are multiplied up rather than discarded — that recovers
  25,055 rows in award_records_v2 alone. The factor is confirmed by the
  median estimate/award ratio of 1.1e7 for these rows.
* After rescaling, amounts outside (1e3, 1e11) are dropped. 99 rows exceed
  the ceiling with values up to 2.6e15 (SHARK Limited, Techno Drugs) against
  a 99.9th percentile of 6.6e8; they are unit errors that would otherwise
  dominate every total.
* NPPI is computed as award/estimate, not read from the stored ``npp_ratio``
  column, which is populated on 9.4% of rows and holds impossible values
  (max 99827; BWDB averaging 57.8). Computed fresh it yields a 0.943 median
  with per-agency medians between 0.90 and 1.00.

``award_date`` is stored as text in 'DD-Mon-YYYY' form, so the year is taken
with a regex rather than a date cast.
"""

from typing import Any, Dict, List, Optional

import time as _time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.base import get_async_session

router = APIRouter(prefix="/market-intelligence", tags=["market-intelligence"])

MIN_AMOUNT_BDT = 1000
MAX_AMOUNT_BDT = 1e11
CRORE_THRESHOLD = 10

# Ratios outside this band are data errors, not negotiating behaviour.
NPPI_MIN = 0.3
NPPI_MAX = 3.0

# Simple TTL cache for expensive aggregates
_cache: Dict[str, Any] = {}
_CACHE_TTL = 300  # 5 minutes


def _rescaled(col: str) -> str:
    """Lift crore-denominated values into taka."""
    return (
        f"(CASE WHEN {col} > 0 AND {col} < {CRORE_THRESHOLD} "
        f"THEN {col} * 1e7 ELSE {col} END)"
    )


# award_records_v2
AMT = _rescaled("amount_bdt")
AWARD_OK = f"{AMT} > {MIN_AMOUNT_BDT} AND {AMT} < {MAX_AMOUNT_BDT}"
AWARD_YEAR = "substring(award_date from '\\d{4}')::int"

# procurement_lifecycle, used only for NPPI
_LC_AMT = _rescaled("award_amount_bdt")
_NPPI_OK = (
    f"estimated_cost_bdt > {MIN_AMOUNT_BDT} "
    f"AND {_LC_AMT} > {MIN_AMOUNT_BDT} AND {_LC_AMT} < {MAX_AMOUNT_BDT} "
    f"AND {_LC_AMT} / estimated_cost_bdt BETWEEN {NPPI_MIN} AND {NPPI_MAX}"
)
_NPPI_EXPR = f"{_LC_AMT} / estimated_cost_bdt"


async def _rows(db: AsyncSession, sql: str, params: Dict[str, Any] | None = None) -> List[Dict]:
    result = await db.execute(text(sql), params or {})
    return [dict(r) for r in result.mappings()]


@router.get("/overview")
async def get_overview(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Headline market figures across the award record."""
    try:
        cache_key = "overview"
        cached = _cache.get(cache_key)
        if cached and (_time.time() - cached.get("_ts", 0)) < _CACHE_TTL:
            return cached

        rows = await _rows(db, f"""
            SELECT
                count(*)                                   AS total_records,
                count(*) FILTER (WHERE {AWARD_OK})         AS awarded_count,
                count(DISTINCT agency_code) FILTER (
                    WHERE agency_code IS NOT NULL AND agency_code <> '') AS agency_count,
                count(DISTINCT contractor_name) FILTER (
                    WHERE contractor_name IS NOT NULL AND contractor_name <> '') AS contractor_count,
                COALESCE(sum({AMT}) FILTER (WHERE {AWARD_OK}), 0)  AS total_awarded_bdt,
                COALESCE(avg({AMT}) FILTER (WHERE {AWARD_OK}), 0)  AS avg_award_bdt,
                COALESCE(percentile_cont(0.5) WITHIN GROUP (
                    ORDER BY {AMT}) FILTER (WHERE {AWARD_OK}), 0)  AS median_award_bdt
            FROM award_records_v2
        """)
        overview = rows[0] if rows else {}

        nppi = await _rows(db, f"""
            SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY {_NPPI_EXPR}) AS median_nppi,
                   count(*) AS nppi_sample
            FROM procurement_lifecycle
            WHERE {_NPPI_OK}
        """)
        overview.update(nppi[0] if nppi else {"median_nppi": None, "nppi_sample": 0})
        overview["_ts"] = _time.time()
        _cache[cache_key] = overview
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/award-history")
async def get_award_history(
    years: int = Query(8, ge=1, le=25),
    agency: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[Dict[str, Any]]:
    """Awards per year: volume, value, distinct contractors and median NPPI."""
    try:
        agency_clause = "AND agency_code = :agency" if agency else ""
        params: Dict[str, Any] = {"years": years}
        if agency:
            params["agency"] = agency

        awards = await _rows(db, f"""
            SELECT
                {AWARD_YEAR}          AS year,
                count(*)              AS award_count,
                sum({AMT})            AS total_value_bdt,
                avg({AMT})            AS avg_value_bdt,
                count(DISTINCT contractor_name) FILTER (
                    WHERE contractor_name IS NOT NULL AND contractor_name <> '') AS contractor_count
            FROM award_records_v2
            WHERE award_date ~ '\\d{{4}}' AND {AWARD_OK} {agency_clause}
            GROUP BY 1
            HAVING {AWARD_YEAR} BETWEEN
                   EXTRACT(YEAR FROM CURRENT_DATE)::int - :years
                   AND EXTRACT(YEAR FROM CURRENT_DATE)::int
            ORDER BY 1 DESC
        """, params)

        nppi = await _rows(db, f"""
            SELECT substring(award_date from '\\d{{4}}')::int AS year,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY {_NPPI_EXPR}) AS median_nppi
            FROM procurement_lifecycle
            WHERE award_date ~ '\\d{{4}}' AND {_NPPI_OK} {agency_clause}
            GROUP BY 1
        """, params)

        by_year = {r["year"]: r["median_nppi"] for r in nppi}
        for row in awards:
            row["median_nppi"] = by_year.get(row["year"])
        return awards
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agencies")
async def get_agency_behaviour(
    limit: int = Query(15, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[Dict[str, Any]]:
    """How each agency awards: volume, typical size, discount and concentration.

    ``contractor_concentration`` is the share of an agency's awards taken by
    its single most frequent winner — a rough read on how contestable its
    pipeline is.
    """
    try:
        cache_key = f"agencies:{limit}"
        cached = _cache.get(cache_key)
        if cached and (_time.time() - cached.get("_ts", 0)) < _CACHE_TTL:
            return cached.get("data", [])
        rows = await _rows(db, f"""
            WITH base AS (
                SELECT agency_code, contractor_name, {AMT} AS amt
                FROM award_records_v2
                WHERE agency_code IS NOT NULL AND agency_code <> '' AND {AWARD_OK}
            ),
            agg AS (
                SELECT agency_code,
                       count(*)                                  AS award_count,
                       sum(amt)                                  AS total_value_bdt,
                       avg(amt)                                  AS avg_value_bdt,
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY amt) AS median_value_bdt,
                       count(DISTINCT contractor_name) FILTER (
                           WHERE contractor_name IS NOT NULL AND contractor_name <> '') AS contractor_count
                FROM base GROUP BY agency_code
            ),
            top_winner AS (
                SELECT DISTINCT ON (agency_code) agency_code,
                       contractor_name AS top_contractor, count(*) AS top_wins
                FROM base
                WHERE contractor_name IS NOT NULL AND contractor_name <> ''
                GROUP BY agency_code, contractor_name
                ORDER BY agency_code, count(*) DESC
            )
            SELECT a.*, t.top_contractor, t.top_wins,
                   ROUND((t.top_wins::numeric / NULLIF(a.award_count,0)) * 100, 1)
                       AS contractor_concentration_pct
            FROM agg a LEFT JOIN top_winner t USING (agency_code)
            ORDER BY a.award_count DESC
            LIMIT :limit
        """, {"limit": limit})

        nppi = await _rows(db, f"""
            SELECT agency_code,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY {_NPPI_EXPR}) AS median_nppi
            FROM procurement_lifecycle
            WHERE {_NPPI_OK} AND agency_code IS NOT NULL AND agency_code <> ''
            GROUP BY agency_code
        """)
        by_agency = {r["agency_code"]: r["median_nppi"] for r in nppi}
        for row in rows:
            row["median_nppi"] = by_agency.get(row["agency_code"])
        _cache[cache_key] = {"data": rows, "_ts": _time.time()}
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contractors")
async def get_top_contractors(
    limit: int = Query(20, ge=1, le=100),
    agency: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[Dict[str, Any]]:
    """Most active winners, with the discount each typically bids at."""
    try:
        cache_key = f"contractors:{limit}:{agency or ''}"
        cached = _cache.get(cache_key)
        if cached and (_time.time() - cached.get("_ts", 0)) < _CACHE_TTL:
            return cached.get("data", [])
        agency_clause = "AND agency_code = :agency" if agency else ""
        params: Dict[str, Any] = {"limit": limit}
        if agency:
            params["agency"] = agency

        rows = await _rows(db, f"""
            SELECT
                contractor_name,
                count(*)        AS win_count,
                sum({AMT})      AS total_value_bdt,
                avg({AMT})      AS avg_value_bdt,
                max({AMT})      AS largest_award_bdt,
                count(DISTINCT agency_code) FILTER (
                    WHERE agency_code IS NOT NULL AND agency_code <> '') AS agency_count,
                max({AWARD_YEAR}) FILTER (WHERE award_date ~ '\\d{{4}}') AS latest_award_year
            FROM award_records_v2
            WHERE contractor_name IS NOT NULL AND contractor_name <> ''
              AND {AWARD_OK} {agency_clause}
            GROUP BY contractor_name
            ORDER BY win_count DESC
            LIMIT :limit
        """, params)

        # Bidding behaviour is only observable where an estimate exists.
        names = [r["contractor_name"] for r in rows]
        if names:
            nppi = await _rows(db, f"""
                SELECT winner,
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY {_NPPI_EXPR}) AS median_nppi
                FROM procurement_lifecycle
                WHERE {_NPPI_OK} AND winner = ANY(:names)
                GROUP BY winner
            """, {"names": names})
            by_name = {r["winner"]: r["median_nppi"] for r in nppi}
            for row in rows:
                row["median_nppi"] = by_name.get(row["contractor_name"])
        _cache[cache_key] = {"data": rows, "_ts": _time.time()}
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nppi")
async def get_nppi_analysis(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """NPPI distribution overall and by agency.

    A value below 1 means awards land under the published estimate.
    """
    try:
        summary = await _rows(db, f"""
            SELECT count(*) AS sample_size,
                   percentile_cont(0.10) WITHIN GROUP (ORDER BY r) AS p10,
                   percentile_cont(0.25) WITHIN GROUP (ORDER BY r) AS p25,
                   percentile_cont(0.50) WITHIN GROUP (ORDER BY r) AS median,
                   percentile_cont(0.75) WITHIN GROUP (ORDER BY r) AS p75,
                   percentile_cont(0.90) WITHIN GROUP (ORDER BY r) AS p90
            FROM (
                SELECT {_NPPI_EXPR} AS r
                FROM procurement_lifecycle WHERE {_NPPI_OK}
            ) t
        """)

        # ord keeps the buckets in numeric order; labelling alone would sort
        # '100-110%' ahead of '70-85%'.
        buckets = await _rows(db, f"""
            SELECT bucket, count(*) AS count FROM (
                SELECT CASE
                    WHEN r < 0.70 THEN 1 WHEN r < 0.85 THEN 2
                    WHEN r < 0.95 THEN 3 WHEN r < 1.00 THEN 4
                    WHEN r < 1.10 THEN 5 ELSE 6 END AS ord,
                    CASE
                    WHEN r < 0.70 THEN 'under 70%'
                    WHEN r < 0.85 THEN '70-85%'
                    WHEN r < 0.95 THEN '85-95%'
                    WHEN r < 1.00 THEN '95-100%'
                    WHEN r < 1.10 THEN '100-110%'
                    ELSE 'over 110%'
                END AS bucket
                FROM (
                    SELECT {_NPPI_EXPR} AS r
                    FROM procurement_lifecycle WHERE {_NPPI_OK}
                ) x
            ) y GROUP BY ord, bucket ORDER BY ord
        """)

        by_agency = await _rows(db, f"""
            SELECT agency_code,
                   count(*) AS sample_size,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY {_NPPI_EXPR}) AS median_nppi
            FROM procurement_lifecycle
            WHERE {_NPPI_OK} AND agency_code IS NOT NULL AND agency_code <> ''
            GROUP BY agency_code
            HAVING count(*) >= 50
            ORDER BY count(*) DESC
            LIMIT 15
        """)

        return {
            "summary": summary[0] if summary else {},
            "distribution": buckets,
            "by_agency": by_agency,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-district")
async def get_market_by_district(
    limit: int = Query(30, ge=1, le=64),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> List[Dict[str, Any]]:
    """Award volume and value per district.

    Serves the geographic cut the analytics warehouse cannot: vw_market_by_zone
    is empty because dim_zones has zero rows and fact_tenders.zone_id is never
    populated, and its definition uses an invalid EXTRACT(year_month ...) field.
    Rather than repair that three-layer star-schema break, this reads
    award_records_v2.district directly, which is populated on 1,062,494 of
    1,104,451 rows (96%) — the same table every other endpoint here uses. The
    'zone' vocabulary in procurement_lifecycle turned out to be district names
    (Dhaka, Khulna, Bagerhat), so district IS the geographic grain.
    """
    try:
        return await _rows(db, f"""
            SELECT district,
                   count(*)                     AS award_count,
                   count(DISTINCT contractor_name) FILTER (
                       WHERE contractor_name IS NOT NULL AND contractor_name <> '') AS contractor_count,
                   count(DISTINCT agency_code) FILTER (
                       WHERE agency_code IS NOT NULL AND agency_code <> '') AS agency_count,
                   sum({AMT})                   AS total_value_bdt,
                   avg({AMT})                   AS avg_value_bdt,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY {AMT}) AS median_value_bdt
            FROM award_records_v2
            WHERE district IS NOT NULL AND district <> '' AND {AWARD_OK}
            GROUP BY district
            ORDER BY total_value_bdt DESC NULLS LAST
            LIMIT :limit
        """, {"limit": limit})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
