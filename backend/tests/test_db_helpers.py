"""Tests for shared db_helpers and caching layer.

These tests cover the most critical data paths used by multiple agents.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.core.db_helpers import (
    lookup_estimate,
    get_market_discount,
    get_avg_competitors,
    get_market_intelligence,
    get_historical_performance,
    get_competition_risk,
    cache_get,
    cache_set,
    cache_delete,
    get_market_discount_cached,
    get_avg_competitors_cached,
    get_market_intelligence_cached,
    get_historical_performance_cached,
    get_competition_risk_cached,
    lookup_estimate_cached,
    invalidate_market_cache,
)


# ── sync helpers (no DB required) ──────────────────────────────────────────

class TestSyncHelpers:
    def test_lookup_estimate_empty_returns_zero(self):
        assert lookup_estimate("") == 0.0

    def test_get_market_discount_empty_returns_default(self):
        assert get_market_discount("") == 5.5

    def test_get_avg_competitors_empty_returns_default(self):
        assert get_avg_competitors("") == 5

    def test_get_competition_risk_low(self):
        """Agencies with <=3 competitors get 0.70 risk factor."""
        # We can mock the DB by patching get_avg_competitors
        with patch("app.agents.core.db_helpers.get_avg_competitors", return_value=2):
            result = get_competition_risk("BWDB")
        assert result["competition_risk"] == 0.70
        assert result["competitor_count"] == 2

    def test_get_competition_risk_medium(self):
        with patch("app.agents.core.db_helpers.get_avg_competitors", return_value=6):
            result = get_competition_risk("BWDB")
        assert result["competition_risk"] == 1.00
        assert result["competitor_count"] == 6

    def test_get_competition_risk_high(self):
        with patch("app.agents.core.db_helpers.get_avg_competitors", return_value=15):
            result = get_competition_risk("BWDB")
        assert result["competition_risk"] == 1.30
        assert result["competitor_count"] == 15


class TestHistoricalPerformance:
    def test_no_company_name_returns_defaults(self):
        result = get_historical_performance("")
        assert result["win_rate"] == 1.0
        assert result["total_bids"] == 0

    def test_company_with_wins(self):
        with patch("app.agents.core.db_helpers.get_contractor_awards", return_value={"total_awards": 12}):
            result = get_historical_performance("ABC Contractors")
        assert result["wins"] == 12
        assert result["win_rate"] == 1.15
        assert result["total_bids"] == 36


# ── async cache helpers (mock Redis) ───────────────────────────────────────

@pytest.mark.asyncio
class TestRedisCache:
    async def test_cache_get_miss_returns_none(self):
        with patch("app.agents.core.db_helpers._get_redis_cache", return_value=None):
            assert await cache_get("any_key") is None

    async def test_cache_set_without_redis_is_noop(self):
        with patch("app.agents.core.db_helpers._get_redis_cache", return_value=None):
            await cache_set("key", "value")  # should not raise

    async def test_cache_roundtrip(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value='{"avg_discount": 8.5}')
        with patch("app.agents.core.db_helpers._get_redis_cache", return_value=mock_client):
            result = await cache_get("procureflow:cache:market_discount:BWDB:50")
        assert result == {"avg_discount": 8.5}

    async def test_cache_delete(self):
        mock_client = AsyncMock()
        with patch("app.agents.core.db_helpers._get_redis_cache", return_value=mock_client):
            await cache_delete("key")
        mock_client.delete.assert_awaited_once_with("key")

    async def test_invalidate_market_cache(self):
        mock_client = AsyncMock()
        mock_client.scan_iter = MagicMock(return_value=AsyncIterator(["key1", "key2"]))
        with patch("app.agents.core.db_helpers._get_redis_cache", return_value=mock_client):
            await invalidate_market_cache("BWDB")
        mock_client.delete.assert_awaited_once()


class AsyncIterator:
    """Helper to mock async for-await loops."""
    def __init__(self, items):
        self._items = items
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._idx]
        self._idx += 1
        return item


# ── cached wrappers (mock underlying + cache) ───────────────────────────────

@pytest.mark.asyncio
class TestCachedWrappers:
    async def test_get_market_discount_cached_hit(self):
        with patch("app.agents.core.db_helpers.cache_get", return_value=7.5):
            result = await get_market_discount_cached("BWDB")
        assert result == 7.5

    async def test_get_market_discount_cached_miss(self):
        with patch("app.agents.core.db_helpers.cache_get", return_value=None):
            with patch("app.agents.core.db_helpers.get_market_discount", return_value=6.0):
                with patch("app.agents.core.db_helpers.cache_set") as mock_set:
                    result = await get_market_discount_cached("BWDB")
        assert result == 6.0
        mock_set.assert_awaited_once()

    async def test_lookup_estimate_cached_empty(self):
        assert await lookup_estimate_cached("") == 0.0


# ── pool configuration sanity check ─────────────────────────────────────────

class TestDatabasePoolConfig:
    def test_pool_sizes_bumped(self):
        """Verify that database.py configures pool_size=20 / max_overflow=40."""
        # Read the source file and assert the values are present
        import pathlib, re
        db_file = pathlib.Path(__file__).parent.parent / "app" / "db" / "database.py"
        content = db_file.read_text()
        pool_sizes = re.findall(r"pool_size=(\d+)", content)
        max_overflows = re.findall(r"max_overflow=(\d+)", content)
        assert "20" in pool_sizes, f"Expected pool_size=20, found {pool_sizes}"
        assert "40" in max_overflows, f"Expected max_overflow=40, found {max_overflows}"
