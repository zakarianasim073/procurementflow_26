"""Shared database helpers for agents.

Extracts duplicate SQL queries from win_probability, bid_position_optimizer,
and competitor_intelligence into a single service layer with optional caching.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.db.database import get_sync_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Simple in-memory cache for read-only market aggregates (5-minute TTL)
_cache: Dict[str, Any] = {}
_cache_time: Dict[str, float] = {}


def _cache_key(func: str, **kwargs) -> str:
    return f"{func}:{hash(tuple(sorted(kwargs.items())))}"


def _get_cached(key: str, ttl_seconds: float = 300.0) -> Any:
    import time
    ts = _cache_time.get(key)
    if ts and (time.time() - ts) < ttl_seconds:
        return _cache.get(key)
    return None


def _set_cached(key: str, value: Any) -> None:
    import time
    _cache[key] = value
    _cache_time[key] = time.time()


def lookup_estimate(tender_id: str) -> float:
    """Look up the estimated cost for a tender from app_records or npp_records."""
    if not tender_id:
        return 0.0
    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT estimated_cost_bdt FROM app_records WHERE source_tender_id = :tid LIMIT 1"
                ),
                {"tid": tender_id},
            ).fetchone()
            if row and row[0]:
                return float(row[0])
            row = conn.execute(
                text(
                    "SELECT estimated_amount_bdt FROM npp_records WHERE tender_id = :tid AND estimated_amount_bdt > 0 LIMIT 1"
                ),
                {"tid": tender_id},
            ).fetchone()
            if row and row[0]:
                return float(row[0])
    except Exception as e:
        logger.warning(f"Estimate lookup error for {tender_id}: {e}")
    return 0.0


def get_market_discount(agency: str, limit: int = 50) -> float:
    """Return average discount percentage below OE for an agency."""
    if not agency:
        return 5.5
    cache_key = _cache_key("market_discount", agency=agency, limit=limit)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT lowest_percent_below_oe FROM npp_records "
                    "WHERE agency = :agency AND lowest_percent_below_oe > 0 "
                    "AND lowest_percent_below_oe < 50 LIMIT :limit"
                ),
                {"agency": agency, "limit": limit},
            ).fetchall()
            vals = [float(r[0]) for r in rows if r[0] is not None]
            result = round(sum(vals) / len(vals), 2) if vals else 5.5
            _set_cached(cache_key, result)
            return result
    except Exception as e:
        logger.warning(f"Market discount error for {agency}: {e}")
    return 5.5


def get_avg_competitors(agency: str, limit: int = 20) -> int:
    """Return average number of bidders for an agency from opening reports."""
    if not agency:
        return 5
    cache_key = _cache_key("avg_competitors", agency=agency, limit=limit)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT json_array_length(bidders) AS bidder_count FROM opening_reports "
                    "WHERE pe_office LIKE :agency AND bidders IS NOT NULL LIMIT :limit"
                ),
                {"agency": f"%{agency}%", "limit": limit},
            ).fetchall()
            counts = [float(r[0]) for r in rows if r[0] is not None]
            result = int(round(sum(counts) / len(counts), 0)) if counts else 5
            _set_cached(cache_key, result)
            return result
    except Exception as e:
        logger.warning(f"Competitor count error for {agency}: {e}")
    return 5


def get_market_intelligence(agency: str, zone: str = None) -> Dict[str, Any]:
    """Return combined market intelligence (discount + competition) for an agency."""
    return {
        "avg_discount": get_market_discount(agency),
        "avg_competitors": get_avg_competitors(agency),
    }


def get_contractor_awards(company_name: str, agency: str = None, zone: str = None) -> Dict[str, Any]:
    """Return award statistics for a contractor, optionally filtered by agency or zone."""
    result = {"total_awards": 0, "agency_awards": 0, "zone_awards": 0}
    if not company_name:
        return result

    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            total = conn.execute(
                text(
                    "SELECT COUNT(*) FROM award_records_v2 WHERE contractor_name LIKE :name"
                ),
                {"name": f"%{company_name[:20]}%"},
            ).fetchone()
            result["total_awards"] = total[0] if total else 0

            if agency:
                agency_total = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM award_records_v2 WHERE agency_code = :agency AND contractor_name LIKE :name"
                    ),
                    {"agency": agency, "name": f"%{company_name[:20]}%"},
                ).fetchone()
                result["agency_awards"] = agency_total[0] if agency_total else 0

            if zone:
                zone_total = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM award_records_v2 WHERE district = :zone AND contractor_name LIKE :name"
                    ),
                    {"zone": zone, "name": f"%{company_name[:20]}%"},
                ).fetchone()
                result["zone_awards"] = zone_total[0] if zone_total else 0

    except Exception as e:
        logger.warning(f"Contractor award error for {company_name}: {e}")

    return result


def query_awards_for_competitor_analysis(limit: int = 500) -> List[Dict[str, Any]]:
    """Query award_records_v2 joined with npp_records for competitor intelligence."""
    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT a.contractor_name AS winner,
                           a.amount_bdt AS award_amount,
                           COALESCE(a.agency_code, a.pe_office, '') AS procuring_entity,
                           COALESCE(n.lowest_percent_below_oe, 0) AS discount_percent,
                           'Construction' AS category
                    FROM award_records_v2 a
                    LEFT JOIN npp_records n ON a.source_tender_id = n.tender_id
                    WHERE a.contractor_name IS NOT NULL
                      AND a.contractor_name != ''
                    ORDER BY a.amount_bdt DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).fetchall()
            if rows:
                return [dict(r._mapping) for r in rows]
    except Exception as e:
        logger.debug(f"DB awards query failed: {e}")
    return []


def get_competition_risk(agency: str) -> Dict[str, Any]:
    """Return competition risk assessment for an agency."""
    avg_competitors = get_avg_competitors(agency)
    if avg_competitors <= 3:
        competition_risk = 0.70
    elif avg_competitors <= 5:
        competition_risk = 0.85
    elif avg_competitors <= 8:
        competition_risk = 1.00
    elif avg_competitors <= 12:
        competition_risk = 1.15
    else:
        competition_risk = 1.30

    return {
        "competition_risk": competition_risk,
        "competitor_count": avg_competitors,
        "syndicate_risk": False,
    }


def get_historical_performance(company_name: str) -> Dict[str, Any]:
    """Return historical win-rate statistics for a contractor."""
    result = {"win_rate": 1.0, "total_bids": 0, "wins": 0}
    if not company_name:
        return result

    awards = get_contractor_awards(company_name)
    wins = awards.get("total_awards", 0)
    result["wins"] = wins
    result["total_bids"] = max(wins * 3, 10)

    if wins > 10:
        result["win_rate"] = 1.15
    elif wins > 5:
        result["win_rate"] = 1.05
    elif wins > 2:
        result["win_rate"] = 0.95
    else:
        result["win_rate"] = 0.80

    return result


# ── Async variants (avoid blocking the event loop) ─────────────────────

from app.db.database import get_async_session


async def lookup_estimate_async(tender_id: str) -> float:
    """Async version of lookup_estimate."""
    if not tender_id:
        return 0.0
    try:
        async with get_async_session() as session:
            row = (await session.execute(
                text(
                    "SELECT estimated_cost_bdt FROM app_records WHERE source_tender_id = :tid LIMIT 1"
                ),
                {"tid": tender_id},
            )).fetchone()
            if row and row[0]:
                return float(row[0])
            row = (await session.execute(
                text(
                    "SELECT estimated_amount_bdt FROM npp_records WHERE tender_id = :tid AND estimated_amount_bdt > 0 LIMIT 1"
                ),
                {"tid": tender_id},
            )).fetchone()
            if row and row[0]:
                return float(row[0])
    except Exception as e:
        logger.warning(f"Async estimate lookup error for {tender_id}: {e}")
    return 0.0


async def get_market_discount_async(agency: str, limit: int = 50) -> float:
    """Async version of get_market_discount."""
    if not agency:
        return 5.5
    cache_key = _cache_key("market_discount", agency=agency, limit=limit)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        async with get_async_session() as session:
            rows = (await session.execute(
                text(
                    "SELECT lowest_percent_below_oe FROM npp_records "
                    "WHERE agency = :agency AND lowest_percent_below_oe > 0 "
                    "AND lowest_percent_below_oe < 50 LIMIT :limit"
                ),
                {"agency": agency, "limit": limit},
            )).fetchall()
            vals = [float(r[0]) for r in rows if r[0] is not None]
            result = round(sum(vals) / len(vals), 2) if vals else 5.5
            _set_cached(cache_key, result)
            return result
    except Exception as e:
        logger.warning(f"Async market discount error for {agency}: {e}")
    return 5.5


async def get_avg_competitors_async(agency: str, limit: int = 20) -> int:
    """Async version of get_avg_competitors."""
    if not agency:
        return 5
    cache_key = _cache_key("avg_competitors", agency=agency, limit=limit)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        async with get_async_session() as session:
            rows = (await session.execute(
                text(
                    "SELECT json_array_length(bidders) AS bidder_count FROM opening_reports "
                    "WHERE pe_office LIKE :agency AND bidders IS NOT NULL LIMIT :limit"
                ),
                {"agency": f"%{agency}%", "limit": limit},
            )).fetchall()
            counts = [float(r[0]) for r in rows if r[0] is not None]
            result = int(round(sum(counts) / len(counts), 0)) if counts else 5
            _set_cached(cache_key, result)
            return result
    except Exception as e:
        logger.warning(f"Async competitor count error for {agency}: {e}")
    return 5


async def get_market_intelligence_async(agency: str, zone: str = None) -> Dict[str, Any]:
    """Async version of get_market_intelligence."""
    return {
        "avg_discount": await get_market_discount_async(agency),
        "avg_competitors": await get_avg_competitors_async(agency),
    }


async def get_historical_performance_async(company_name: str) -> Dict[str, Any]:
    """Async version of get_historical_performance."""
    result = {"win_rate": 1.0, "total_bids": 0, "wins": 0}
    if not company_name:
        return result

    try:
        async with get_async_session() as session:
            award_count = (await session.execute(
                text(
                    "SELECT COUNT(*) FROM award_records_v2 WHERE contractor_name LIKE :name"
                ),
                {"name": f"%{company_name[:20]}%"},
            )).fetchone()

            wins = award_count[0] if award_count else 0
            result["wins"] = wins
            result["total_bids"] = max(wins * 3, 10)

            if wins > 10:
                result["win_rate"] = 1.15
            elif wins > 5:
                result["win_rate"] = 1.05
            elif wins > 2:
                result["win_rate"] = 0.95
            else:
                result["win_rate"] = 0.80

    except Exception as e:
        logger.warning(f"Async historical performance error for {company_name}: {e}")

    return result


async def get_competition_risk_async(agency: str) -> Dict[str, Any]:
    """Async version of get_competition_risk."""
    avg_competitors = await get_avg_competitors_async(agency)
    if avg_competitors <= 3:
        competition_risk = 0.70
    elif avg_competitors <= 5:
        competition_risk = 0.85
    elif avg_competitors <= 8:
        competition_risk = 1.00
    elif avg_competitors <= 12:
        competition_risk = 1.15
    else:
        competition_risk = 1.30

    return {
        "competition_risk": competition_risk,
        "competitor_count": avg_competitors,
        "syndicate_risk": False,
    }


# ── Redis-backed query cache (general purpose, not just agent memory) ─────

_redis_cache_client = None


async def _get_redis_cache():
    """Get a shared Redis client for general query caching."""
    global _redis_cache_client
    if _redis_cache_client is None:
        redis_url = getattr(config, 'redis_url', '') or os.getenv("REDIS_URL", "")
        if redis_url:
            try:
                import redis.asyncio as redis
                _redis_cache_client = redis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                logger.debug(f"Redis cache not available: {e}")
    return _redis_cache_client


async def cache_get(key: str) -> Optional[Any]:
    """Get a value from the Redis cache."""
    client = await _get_redis_cache()
    if not client:
        return None
    try:
        cached = await client.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    """Set a value in the Redis cache with TTL."""
    client = await _get_redis_cache()
    if not client:
        return
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception as e:
        logger.debug(f"Redis cache set failed: {e}")


async def cache_delete(key: str):
    """Delete a key from the Redis cache."""
    client = await _get_redis_cache()
    if not client:
        return
    try:
        await client.delete(key)
    except Exception:
        pass


async def get_market_discount_cached(agency: str, limit: int = 50, ttl: int = 300) -> float:
    """Return cached market discount; falls back to DB and populates cache."""
    if not agency:
        return 5.5
    cache_key = f"procureflow:cache:market_discount:{agency}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    result = get_market_discount(agency, limit)
    await cache_set(cache_key, result, ttl)
    return result


async def get_avg_competitors_cached(agency: str, limit: int = 20, ttl: int = 300) -> int:
    """Return cached average competitor count; falls back to DB and populates cache."""
    if not agency:
        return 5
    cache_key = f"procureflow:cache:avg_competitors:{agency}:{limit}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    result = get_avg_competitors(agency, limit)
    await cache_set(cache_key, result, ttl)
    return result


async def get_market_intelligence_cached(agency: str, zone: str = None, ttl: int = 300) -> Dict[str, Any]:
    """Return cached combined market intelligence."""
    cache_key = f"procureflow:cache:market_intel:{agency}:{zone or 'all'}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    result = await get_market_intelligence_async(agency, zone)
    await cache_set(cache_key, result, ttl)
    return result


async def get_historical_performance_cached(company_name: str, ttl: int = 300) -> Dict[str, Any]:
    """Return cached contractor performance stats."""
    if not company_name:
        return {"win_rate": 1.0, "total_bids": 0, "wins": 0}
    cache_key = f"procureflow:cache:contractor_perf:{company_name[:30]}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    result = await get_historical_performance_async(company_name)
    await cache_set(cache_key, result, ttl)
    return result


async def get_competition_risk_cached(agency: str, ttl: int = 300) -> Dict[str, Any]:
    """Return cached competition risk assessment."""
    cache_key = f"procureflow:cache:comp_risk:{agency or 'all'}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    result = await get_competition_risk_async(agency)
    await cache_set(cache_key, result, ttl)
    return result


async def lookup_estimate_cached(tender_id: str, ttl: int = 300) -> float:
    """Return cached estimate lookup."""
    if not tender_id:
        return 0.0
    cache_key = f"procureflow:cache:estimate:{tender_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    result = await lookup_estimate_async(tender_id)
    await cache_set(cache_key, result, ttl)
    return result


async def invalidate_market_cache(agency: str = None):
    """Invalidate all market-related cache keys (e.g., after data import)."""
    client = await _get_redis_cache()
    if not client:
        return
    try:
        pattern = f"procureflow:cache:market_*:{agency or '*'}*"
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await client.delete(*keys)
            logger.info("Invalidated %d market cache keys for agency=%s", len(keys), agency or "all")
    except Exception as e:
        logger.debug(f"Cache invalidation failed: {e}")
