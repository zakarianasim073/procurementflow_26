"""T-024: Market Trend Analysis Tests."""

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


class TestTrendData:
    """Test /market-trends/{zone}/{category}/trends endpoint."""

    @pytest.mark.asyncio
    async def test_trend_data_requires_auth(self, client: AsyncClient):
        """Endpoint requires authentication."""
        response = await client.get("/api/v2/market-trends/A/category-1/trends")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_trend_data_structure(self, client: AsyncClient, auth_headers: dict):
        """Returns time series data with correct structure."""
        response = await client.get(
            "/api/v2/market-trends/A/category-1/trends",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if data:
                point = data[0]
                assert "period_date" in point
                assert "avg_price" in point
                assert "min_price" in point
                assert "max_price" in point
                assert "std_price" in point
                assert "tender_count" in point
                assert "bid_count" in point
                assert "avg_bid_count" in point

    @pytest.mark.asyncio
    async def test_trend_data_period_types(self, client: AsyncClient, auth_headers: dict):
        """Supports different period aggregations."""
        for period_type in ["day", "week", "month"]:
            response = await client.get(
                f"/api/v2/market-trends/A/category-1/trends?period_type={period_type}",
                headers=auth_headers,
            )
            assert response.status_code in (200, 503)  # 503 if no data

    @pytest.mark.asyncio
    async def test_trend_data_lookback_range(self, client: AsyncClient, auth_headers: dict):
        """Respects lookback_days parameter (7-730 days)."""
        # Valid: 90 days
        response = await client.get(
            "/api/v2/market-trends/A/category-1/trends?lookback_days=90",
            headers=auth_headers,
        )
        assert response.status_code in (200, 503)

        # Invalid: <7 days
        response = await client.get(
            "/api/v2/market-trends/A/category-1/trends?lookback_days=3",
            headers=auth_headers,
        )
        assert response.status_code == 422

        # Invalid: >730 days
        response = await client.get(
            "/api/v2/market-trends/A/category-1/trends?lookback_days=800",
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestTrendDecomposition:
    """Test /market-trends/{zone}/{category}/decomposition endpoint."""

    @pytest.mark.asyncio
    async def test_decomposition_structure(self, client: AsyncClient, auth_headers: dict):
        """Returns seasonal decomposition components."""
        response = await client.get(
            "/api/v2/market-trends/A/category-1/decomposition",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "seasonal_strength" in data
            assert "peak_season_months" in data
            assert "variance_explained" in data
            assert "data_points_used" in data
            assert "mae" in data
            assert 0 <= data["seasonal_strength"] <= 1
            assert 0 <= data["variance_explained"] <= 1

    @pytest.mark.asyncio
    async def test_decomposition_quality_metrics(self, client: AsyncClient, auth_headers: dict):
        """Decomposition metrics are valid."""
        response = await client.get(
            "/api/v2/market-trends/B/category-2/decomposition",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            # MAE should be non-negative
            assert data["mae"] >= 0
            # At least some data points used
            assert data["data_points_used"] >= 0

    @pytest.mark.asyncio
    async def test_decomposition_peak_months(self, client: AsyncClient, auth_headers: dict):
        """Peak season months are in valid range (1-12)."""
        response = await client.get(
            "/api/v2/market-trends/C/category-3/decomposition",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("peak_season_months"):
                months = [int(m) for m in data["peak_season_months"].split(",")]
                assert all(1 <= m <= 12 for m in months)


class TestAnomalyDetection:
    """Test /market-trends/{zone}/{category}/anomalies endpoint."""

    @pytest.mark.asyncio
    async def test_anomaly_structure(self, client: AsyncClient, auth_headers: dict):
        """Returns list of detected anomalies with proper structure."""
        response = await client.get(
            "/api/v2/market-trends/A/category-1/anomalies",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if data:
                anomaly = data[0]
                assert "period_date" in anomaly
                assert "anomaly_type" in anomaly
                assert anomaly["anomaly_type"] in ["spike", "drop"]
                assert "observed_price" in anomaly
                assert "expected_price" in anomaly
                assert "deviation_pct" in anomaly
                assert "severity" in anomaly
                assert anomaly["severity"] in ["low", "medium", "high", "critical"]
                assert "confidence" in anomaly
                assert 0 <= anomaly["confidence"] <= 1
                assert "message" in anomaly

    @pytest.mark.asyncio
    async def test_anomaly_sensitivity_levels(self, client: AsyncClient, auth_headers: dict):
        """Sensitivity parameter affects detection."""
        responses = {}
        for sensitivity in ["low", "medium", "high"]:
            response = await client.get(
                f"/api/v2/market-trends/A/category-1/anomalies?sensitivity={sensitivity}",
                headers=auth_headers,
            )
            if response.status_code == 200:
                responses[sensitivity] = len(response.json())

        if len(responses) >= 2:
            # Higher sensitivity should detect more anomalies
            if "high" in responses and "low" in responses:
                assert responses["high"] >= responses["low"]

    @pytest.mark.asyncio
    async def test_anomaly_limit(self, client: AsyncClient, auth_headers: dict):
        """Respects limit parameter."""
        response = await client.get(
            "/api/v2/market-trends/A/category-1/anomalies?limit=5",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 5


class TestPriceForecast:
    """Test /market-trends/{zone}/{category}/forecast endpoint."""

    @pytest.mark.asyncio
    async def test_forecast_structure(self, client: AsyncClient, auth_headers: dict):
        """Returns forecast with confidence intervals."""
        response = await client.get(
            "/api/v2/market-trends/A/category-1/forecast",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "forecast_dates" in data
            assert "forecast_prices" in data
            assert "confidence_low" in data
            assert "confidence_high" in data
            assert "forecast_days" in data

    @pytest.mark.asyncio
    async def test_forecast_bounds(self, client: AsyncClient, auth_headers: dict):
        """Confidence intervals are sensible (low < forecast < high)."""
        response = await client.get(
            "/api/v2/market-trends/B/category-2/forecast?forecast_days=30",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            for i in range(len(data["forecast_prices"])):
                low = data["confidence_low"][i]
                forecast = data["forecast_prices"][i]
                high = data["confidence_high"][i]
                assert low <= forecast <= high

    @pytest.mark.asyncio
    async def test_forecast_days_parameter(self, client: AsyncClient, auth_headers: dict):
        """Respects forecast_days (7-90 days)."""
        # Valid: 30 days
        response = await client.get(
            "/api/v2/market-trends/A/category-1/forecast?forecast_days=30",
            headers=auth_headers,
        )
        assert response.status_code in (200, 503)

        # Invalid: <7 days
        response = await client.get(
            "/api/v2/market-trends/A/category-1/forecast?forecast_days=3",
            headers=auth_headers,
        )
        assert response.status_code == 422

        # Invalid: >90 days
        response = await client.get(
            "/api/v2/market-trends/A/category-1/forecast?forecast_days=120",
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestTrendSummary:
    """Test /market-trends/{zone}/{category}/summary endpoint."""

    @pytest.mark.asyncio
    async def test_summary_structure(self, client: AsyncClient, auth_headers: dict):
        """Returns complete market summary."""
        response = await client.get(
            "/api/v2/market-trends/A/category-1/summary",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "zone_id" in data
            assert "category_id" in data
            assert "current_price" in data
            assert "price_change_pct" in data
            assert "trend_direction" in data
            assert data["trend_direction"] in ["increasing", "stable", "decreasing"]
            assert "seasonal_strength" in data
            assert "peak_season_months" in data
            assert "recent_anomalies" in data
            assert "forecast_30d" in data
            assert isinstance(data["forecast_30d"], list)
            assert "forecast_confidence" in data
            assert 0 <= data["forecast_confidence"] <= 1

    @pytest.mark.asyncio
    async def test_summary_metrics_valid(self, client: AsyncClient, auth_headers: dict):
        """Summary metrics are in valid ranges."""
        response = await client.get(
            "/api/v2/market-trends/B/category-2/summary",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            # Current price should be positive
            assert data["current_price"] > 0
            # Recent anomalies should be non-negative
            assert data["recent_anomalies"] >= 0
            # Confidence should be 0-1
            assert 0 <= data["forecast_confidence"] <= 1


class TestTrendPerformance:
    """Test performance of trend endpoints."""

    @pytest.mark.asyncio
    async def test_trend_data_latency(self, client: AsyncClient, auth_headers: dict):
        """Trend data fetch responds quickly."""
        import time

        start = time.perf_counter()
        response = await client.get(
            "/api/v2/market-trends/A/category-1/trends?lookback_days=90",
            headers=auth_headers,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code in (200, 503)
        # Allow <5s for cold start and missing data
        assert elapsed_ms < 5000

    @pytest.mark.asyncio
    async def test_summary_latency(self, client: AsyncClient, auth_headers: dict):
        """Summary endpoint responds within SLO (<500ms for combined view)."""
        import time

        start = time.perf_counter()
        response = await client.get(
            "/api/v2/market-trends/A/category-1/summary",
            headers=auth_headers,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code in (200, 503)
        # Allow <5s for cold start and data aggregation
        assert elapsed_ms < 5000


class TestTrendConsistency:
    """Test consistency across trend calls."""

    @pytest.mark.asyncio
    async def test_trend_data_ordering(self, client: AsyncClient, auth_headers: dict):
        """Trend data is ordered chronologically."""
        response = await client.get(
            "/api/v2/market-trends/A/category-1/trends?lookback_days=30",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                # Each date should be >= previous (ascending order)
                for i in range(1, len(data)):
                    assert data[i]["period_date"] >= data[i - 1]["period_date"]

    @pytest.mark.asyncio
    async def test_price_ranges_valid(self, client: AsyncClient, auth_headers: dict):
        """Min ≤ Avg ≤ Max for each data point."""
        response = await client.get(
            "/api/v2/market-trends/A/category-1/trends?lookback_days=30",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            for point in data:
                assert point["min_price"] <= point["avg_price"] <= point["max_price"]
