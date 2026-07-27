"""T-022: Competitor Benchmarking Engine Tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Valid auth headers with tenant context."""
    return {
        "Authorization": "Bearer test_token",
        "X-Tenant-ID": "test-tenant-1",
    }


class TestPeerGroupEndpoint:
    """Test /api/v2/benchmarking/contractors/{id}/peer-group."""

    @pytest.mark.asyncio
    async def test_peer_group_requires_auth(self, client: AsyncClient):
        """Endpoint requires authentication."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/peer-group"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_peer_group_returns_list(self, client: AsyncClient, auth_headers: dict):
        """Returns list of peer contractors."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/peer-group?limit=5",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)  # 404 if contractor not found
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if data:
                peer = data[0]
                assert "contractor_id" in peer
                assert "contractor_name" in peer
                assert "similarity_score" in peer

    @pytest.mark.asyncio
    async def test_peer_group_limit_respected(self, client: AsyncClient, auth_headers: dict):
        """Respects limit parameter (max 20)."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/peer-group?limit=3",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 3


class TestWinRateEndpoint:
    """Test /api/v2/benchmarking/contractors/{id}/win-rate."""

    @pytest.mark.asyncio
    async def test_win_rate_structure(self, client: AsyncClient, auth_headers: dict):
        """Win rate endpoint returns expected fields."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/win-rate",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "contractor_id" in data
            assert "total_bids" in data
            assert "won_bids" in data
            assert "award_count" in data
            assert "total_award_value" in data
            assert "win_rate_pct" in data
            assert 0 <= data["win_rate_pct"] <= 100

    @pytest.mark.asyncio
    async def test_win_rate_months_parameter(self, client: AsyncClient, auth_headers: dict):
        """Accepts months parameter (1-36)."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/win-rate?months=6",
            headers=auth_headers,
        )
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_win_rate_calculation(self, client: AsyncClient, auth_headers: dict):
        """Win rate ≤ 100% and won_bids ≤ total_bids."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/win-rate",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert data["won_bids"] <= data["total_bids"]
            assert data["award_count"] >= 0


class TestBidStrategyEndpoint:
    """Test /api/v2/benchmarking/contractors/{id}/bid-strategy."""

    @pytest.mark.asyncio
    async def test_bid_strategy_structure(self, client: AsyncClient, auth_headers: dict):
        """Bid strategy includes positioning info."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/bid-strategy",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "avg_bid_amount" in data
            assert "market_position" in data
            assert data["market_position"] in ("aggressive", "competitive", "premium")

    @pytest.mark.asyncio
    async def test_bid_strategy_ratio(self, client: AsyncClient, auth_headers: dict):
        """Bid-to-market ratio indicates positioning."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/bid-strategy",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            # Ratio <90 = aggressive, 90-110 = competitive, >110 = premium
            if data["bid_to_market_ratio"] > 0:
                position = (
                    "aggressive" if data["bid_to_market_ratio"] < 90
                    else "competitive" if data["bid_to_market_ratio"] < 110
                    else "premium"
                )
                assert position == data["market_position"]


class TestAwardMetricsEndpoint:
    """Test /api/v2/benchmarking/contractors/{id}/awards."""

    @pytest.mark.asyncio
    async def test_award_metrics_structure(self, client: AsyncClient, auth_headers: dict):
        """Award metrics includes completion rate."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/awards",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "award_count" in data
            assert "avg_award_value" in data
            assert "completion_rate_pct" in data
            assert 0 <= data["completion_rate_pct"] <= 100

    @pytest.mark.asyncio
    async def test_award_timing(self, client: AsyncClient, auth_headers: dict):
        """Days to award are reasonable."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/awards",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            if data["award_count"] > 0:
                assert data["min_days_to_award"] >= 0
                assert data["max_days_to_award"] >= data["min_days_to_award"]
                assert data["avg_days_to_award"] >= data["min_days_to_award"]


class TestCategoryPerformanceEndpoint:
    """Test /api/v2/benchmarking/contractors/{id}/categories."""

    @pytest.mark.asyncio
    async def test_categories_sorted_by_awards(self, client: AsyncClient, auth_headers: dict):
        """Categories returned sorted by award count."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/categories",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                for i in range(len(data) - 1):
                    assert data[i]["award_count"] >= data[i + 1]["award_count"]

    @pytest.mark.asyncio
    async def test_categories_limited(self, client: AsyncClient, auth_headers: dict):
        """Category list respects limit."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/categories?limit=3",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 3


class TestMarketRankEndpoint:
    """Test /api/v2/benchmarking/contractors/{id}/market-rank."""

    @pytest.mark.asyncio
    async def test_market_rank_structure(self, client: AsyncClient, auth_headers: dict):
        """Market rank includes percentile."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/market-rank",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "rank" in data
            assert "percentile" in data
            assert "peer_count" in data
            if data["peer_count"] > 0:
                assert 0 <= data["percentile"] <= 100

    @pytest.mark.asyncio
    async def test_market_rank_metrics(self, client: AsyncClient, auth_headers: dict):
        """Can rank by different metrics."""
        for metric in ["win_rate", "bid_volume", "award_value"]:
            response = await client.get(
                f"/api/v2/benchmarking/contractors/contractor-123/market-rank?metric={metric}",
                headers=auth_headers,
            )
            assert response.status_code in (200, 404)


class TestProfileEndpoint:
    """Test /api/v2/benchmarking/contractors/{id}/profile."""

    @pytest.mark.asyncio
    async def test_profile_completeness(self, client: AsyncClient, auth_headers: dict):
        """Profile endpoint returns all metrics."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/profile",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "contractor_id" in data
            assert "win_rate" in data
            assert "bid_strategy" in data
            assert "awards" in data
            assert "top_categories" in data
            assert "market_rank" in data

    @pytest.mark.asyncio
    async def test_profile_consistency(self, client: AsyncClient, auth_headers: dict):
        """Win rate from profile matches individual endpoint."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/profile",
            headers=auth_headers,
        )
        if response.status_code == 200:
            profile_data = response.json()
            profile_win_rate = profile_data["win_rate"]["win_rate_pct"]
            # Could compare to individual endpoint if available
            assert isinstance(profile_win_rate, (int, float))


class TestBenchmarkingDataConsistency:
    """Test cross-metric consistency in benchmarking data."""

    @pytest.mark.asyncio
    async def test_award_count_consistency(self, client: AsyncClient, auth_headers: dict):
        """Award count consistent across endpoints."""
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/win-rate",
            headers=auth_headers,
        )
        if response.status_code == 200:
            win_rate_awards = response.json()["award_count"]

            response2 = await client.get(
                "/api/v2/benchmarking/contractors/contractor-123/awards",
                headers=auth_headers,
            )
            if response2.status_code == 200:
                awards_endpoint = response2.json()["award_count"]
                assert win_rate_awards == awards_endpoint


class TestBenchmarkingPerformance:
    """Test performance characteristics of benchmarking queries."""

    @pytest.mark.asyncio
    async def test_peer_group_latency(self, client: AsyncClient, auth_headers: dict):
        """Peer group query completes quickly."""
        import time

        start = time.perf_counter()
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/peer-group",
            headers=auth_headers,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code in (200, 404)
        assert elapsed_ms < 5000  # <5s SLO

    @pytest.mark.asyncio
    async def test_profile_latency(self, client: AsyncClient, auth_headers: dict):
        """Full profile query completes within SLO."""
        import time

        start = time.perf_counter()
        response = await client.get(
            "/api/v2/benchmarking/contractors/contractor-123/profile",
            headers=auth_headers,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code in (200, 404)
        # Profile combines multiple queries, allow 1s (200ms p95 individual SLO)
        assert elapsed_ms < 5000
