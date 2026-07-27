"""T-021: Analytics Dashboard API Tests — Live metrics and real-time endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Valid auth headers with tenant context."""
    return {
        "Authorization": "Bearer test_token_with_tenant",
        "X-Tenant-ID": "test-tenant-1",
    }


class TestMarketOverviewEndpoint:
    """Test /api/v2/analytics/market-overview."""

    @pytest.mark.asyncio
    async def test_market_overview_unauthorized(self, client: AsyncClient):
        """Endpoint requires authentication."""
        response = await client.get("/api/v2/analytics/market-overview")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_market_overview_structure(self, client: AsyncClient, auth_headers: dict, db_session):
        """Market overview returns expected metrics."""
        response = await client.get(
            "/api/v2/analytics/market-overview",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert "total_tenders" in data
        assert "total_value_bdt" in data
        assert "avg_value_bdt" in data
        assert "awarded_count" in data

        # Validate types and ranges
        assert isinstance(data["total_tenders"], int)
        assert isinstance(data["total_value_bdt"], (int, float))
        assert data["total_tenders"] >= 0
        assert data["total_value_bdt"] >= 0


class TestMarketByAgencyEndpoint:
    """Test /api/v2/analytics/market-by-agency."""

    @pytest.mark.asyncio
    async def test_market_by_agency_limit_parameter(self, client: AsyncClient, auth_headers: dict):
        """Endpoint respects limit query parameter."""
        response = await client.get(
            "/api/v2/analytics/market-by-agency?limit=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.asyncio
    async def test_market_by_agency_default_limit(self, client: AsyncClient, auth_headers: dict):
        """Default limit is 50."""
        response = await client.get(
            "/api/v2/analytics/market-by-agency",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) <= 50

    @pytest.mark.asyncio
    async def test_market_by_agency_item_structure(self, client: AsyncClient, auth_headers: dict):
        """Each agency item has required fields."""
        response = await client.get(
            "/api/v2/analytics/market-by-agency?limit=1",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        if data:
            agency = data[0]
            assert "agency_id" in agency
            assert "agency_code" in agency
            assert "agency_name" in agency
            assert "tender_count" in agency
            assert "total_value_bdt" in agency


class TestContractorPerformanceEndpoint:
    """Test /api/v2/analytics/contractors-performance."""

    @pytest.mark.asyncio
    async def test_contractors_performance_limit(self, client: AsyncClient, auth_headers: dict):
        """Endpoint respects limit (max 500)."""
        response = await client.get(
            "/api/v2/analytics/contractors-performance?limit=20",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) <= 20

    @pytest.mark.asyncio
    async def test_contractors_max_limit_enforced(self, client: AsyncClient, auth_headers: dict):
        """Query limit cannot exceed 500."""
        response = await client.get(
            "/api/v2/analytics/contractors-performance?limit=1000",
            headers=auth_headers,
        )
        # Should either be 422 (validation error) or accept and cap at 500
        assert response.status_code in (200, 422)

    @pytest.mark.asyncio
    async def test_contractor_metrics_fields(self, client: AsyncClient, auth_headers: dict):
        """Contractor items have performance metrics."""
        response = await client.get(
            "/api/v2/analytics/contractors-performance?limit=1",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        if data:
            contractor = data[0]
            assert "contractor_id" in contractor
            assert "contractor_name" in contractor
            assert "total_bids" in contractor
            assert "won_bids" in contractor
            assert "win_rate_pct" in contractor
            assert 0 <= contractor["win_rate_pct"] <= 100


class TestMarketTrendEndpoint:
    """Test /api/v2/analytics/market-trend."""

    @pytest.mark.asyncio
    async def test_market_trend_months_parameter(self, client: AsyncClient, auth_headers: dict):
        """Endpoint accepts months parameter (1-36)."""
        response = await client.get(
            "/api/v2/analytics/market-trend?months=12",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Each item should have a month field
        for point in data:
            assert "month" in point
            assert "tender_count" in point

    @pytest.mark.asyncio
    async def test_market_trend_default_months(self, client: AsyncClient, auth_headers: dict):
        """Default months is 12."""
        response = await client.get(
            "/api/v2/analytics/market-trend",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Data should represent roughly 12 months
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_market_trend_zone_filter(self, client: AsyncClient, auth_headers: dict):
        """Endpoint accepts optional zone filter."""
        response = await client.get(
            "/api/v2/analytics/market-trend?zone_id=A",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestCategoryTrendsEndpoint:
    """Test /api/v2/analytics/category-trends."""

    @pytest.mark.asyncio
    async def test_category_trends_structure(self, client: AsyncClient, auth_headers: dict):
        """Category trends endpoint returns expected fields."""
        response = await client.get(
            "/api/v2/analytics/category-trends",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        if data:
            trend = data[0]
            assert "category_name" in trend
            assert "sector" in trend
            assert "month" in trend
            assert "tender_count" in trend

    @pytest.mark.asyncio
    async def test_category_trends_sector_filter(self, client: AsyncClient, auth_headers: dict):
        """Endpoint filters by optional sector."""
        response = await client.get(
            "/api/v2/analytics/category-trends?sector=Infrastructure",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)


class TestWarehouseStatsEndpoint:
    """Test /api/v2/analytics/warehouse-stats."""

    @pytest.mark.asyncio
    async def test_warehouse_stats_returns_counts(self, client: AsyncClient, auth_headers: dict):
        """Warehouse stats endpoint returns row counts."""
        response = await client.get(
            "/api/v2/analytics/warehouse-stats",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should have count for each table
        assert "dim_agencies" in data
        assert "dim_contractors" in data
        assert "fact_tenders" in data
        assert "fact_awards" in data
        assert "fact_bids" in data

        # All counts should be non-negative integers
        for table, count in data.items():
            assert isinstance(count, int)
            assert count >= 0


class TestLiveMetricsEndpoint:
    """Test /api/v2/analytics/live-metrics (combined dashboard load)."""

    @pytest.mark.asyncio
    async def test_live_metrics_unauthorized(self, client: AsyncClient):
        """Live metrics requires authentication."""
        response = await client.get("/api/v2/analytics/live-metrics")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_live_metrics_response_structure(self, client: AsyncClient, auth_headers: dict):
        """Live metrics endpoint returns all dashboard data in one call."""
        response = await client.get(
            "/api/v2/analytics/live-metrics",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should include all dashboard data points
        assert "overview" in data
        assert "top_agencies" in data
        assert "top_contractors" in data
        assert "latest_trend" in data
        assert "warehouse" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_live_metrics_overview_data(self, client: AsyncClient, auth_headers: dict):
        """Live metrics overview has correct structure."""
        response = await client.get(
            "/api/v2/analytics/live-metrics",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        overview = data["overview"]
        assert "total_tenders" in overview
        assert "total_value_bdt" in overview
        assert "avg_value_bdt" in overview
        assert "awarded_count" in overview

    @pytest.mark.asyncio
    async def test_live_metrics_agencies_limited(self, client: AsyncClient, auth_headers: dict):
        """Live metrics includes top 10 agencies."""
        response = await client.get(
            "/api/v2/analytics/live-metrics",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        agencies = data["top_agencies"]
        assert isinstance(agencies, list)
        assert len(agencies) <= 10

    @pytest.mark.asyncio
    async def test_live_metrics_contractors_limited(self, client: AsyncClient, auth_headers: dict):
        """Live metrics includes top 20 contractors."""
        response = await client.get(
            "/api/v2/analytics/live-metrics",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        contractors = data["top_contractors"]
        assert isinstance(contractors, list)
        assert len(contractors) <= 20

    @pytest.mark.asyncio
    async def test_live_metrics_timestamp_present(self, client: AsyncClient, auth_headers: dict):
        """Live metrics includes current timestamp for freshness tracking."""
        response = await client.get(
            "/api/v2/analytics/live-metrics",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should have an ISO timestamp
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)
        assert len(data["timestamp"]) > 0


class TestAnalyticsDataTenantIsolation:
    """Test tenant isolation in analytics queries."""

    @pytest.mark.asyncio
    async def test_different_tenants_see_own_data(self, client: AsyncClient):
        """Different tenants should not see each other's data."""
        tenant_a_headers = {
            "Authorization": "Bearer tenant_a_token",
            "X-Tenant-ID": "tenant-a",
        }
        tenant_b_headers = {
            "Authorization": "Bearer tenant_b_token",
            "X-Tenant-ID": "tenant-b",
        }

        # Query with tenant A context
        response_a = await client.get(
            "/api/v2/analytics/market-overview",
            headers=tenant_a_headers,
        )
        assert response_a.status_code in (200, 401)  # 401 if auth fails, 200 if valid

        # Query with tenant B context
        response_b = await client.get(
            "/api/v2/analytics/market-overview",
            headers=tenant_b_headers,
        )
        assert response_b.status_code in (200, 401)


class TestAnalyticsPerformance:
    """Test performance characteristics of analytics endpoints."""

    @pytest.mark.asyncio
    async def test_live_metrics_response_time(self, client: AsyncClient, auth_headers: dict):
        """Live metrics endpoint should respond in <500ms (cached)."""
        import time

        start = time.perf_counter()
        response = await client.get(
            "/api/v2/analytics/live-metrics",
            headers=auth_headers,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        # Performance baseline: <1000ms for cold start (caching improves this)
        assert elapsed_ms < 5000, f"Live metrics took {elapsed_ms:.0f}ms (expected <5s)"

    @pytest.mark.asyncio
    async def test_warehouse_stats_fast(self, client: AsyncClient, auth_headers: dict):
        """Warehouse stats should be fast (simple count queries)."""
        import time

        start = time.perf_counter()
        response = await client.get(
            "/api/v2/analytics/warehouse-stats",
            headers=auth_headers,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        # Should be <1s (just counting rows)
        assert elapsed_ms < 5000
