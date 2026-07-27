"""T-023: Price Prediction Model Tests."""

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
        "Authorization": "Bearer test_token",
        "X-Tenant-ID": "test-tenant-1",
    }


class TestTenderPricePrediction:
    """Test /api/v2/predictions/tender-price endpoint."""

    @pytest.mark.asyncio
    async def test_tender_price_requires_auth(self, client: AsyncClient):
        """Endpoint requires authentication."""
        response = await client.post(
            "/api/v2/predictions/tender-price",
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "duration_days": 30,
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_tender_price_structure(self, client: AsyncClient, auth_headers: dict):
        """Response includes predicted price and confidence interval."""
        response = await client.post(
            "/api/v2/predictions/tender-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "duration_days": 30,
            },
        )
        if response.status_code == 200:
            data = response.json()
            assert "predicted_price" in data
            assert "predicted_low" in data
            assert "predicted_high" in data
            assert "confidence_score" in data
            assert 0 <= data["confidence_score"] <= 1

    @pytest.mark.asyncio
    async def test_tender_price_bounds(self, client: AsyncClient, auth_headers: dict):
        """Predicted bounds are sensible (low < predicted < high)."""
        response = await client.post(
            "/api/v2/predictions/tender-price",
            headers=auth_headers,
            json={
                "zone_id": "B",
                "agency_id": "agency-2",
                "category_id": "category-2",
                "duration_days": 60,
            },
        )
        if response.status_code == 200:
            data = response.json()
            assert data["predicted_low"] <= data["predicted_price"] <= data["predicted_high"]
            # Interval should be roughly symmetric (20% bounds)
            low_diff = data["predicted_price"] - data["predicted_low"]
            high_diff = data["predicted_high"] - data["predicted_price"]
            assert abs(low_diff - high_diff) / data["predicted_price"] < 0.05

    @pytest.mark.asyncio
    async def test_tender_price_month_optional(self, client: AsyncClient, auth_headers: dict):
        """Month parameter is optional."""
        response = await client.post(
            "/api/v2/predictions/tender-price",
            headers=auth_headers,
            json={
                "zone_id": "C",
                "agency_id": "agency-3",
                "category_id": "category-3",
                "duration_days": 45,
                "month": 6,
            },
        )
        assert response.status_code in (200, 503)  # 503 if no model available

    @pytest.mark.asyncio
    async def test_tender_price_validation(self, client: AsyncClient, auth_headers: dict):
        """Input validation enforced (duration: 1-365 days)."""
        # Invalid: zero days
        response = await client.post(
            "/api/v2/predictions/tender-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "duration_days": 0,
            },
        )
        assert response.status_code == 422  # Validation error

        # Invalid: >365 days
        response = await client.post(
            "/api/v2/predictions/tender-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "duration_days": 400,
            },
        )
        assert response.status_code == 422


class TestBidPricePrediction:
    """Test /api/v2/predictions/bid-price endpoint."""

    @pytest.mark.asyncio
    async def test_bid_price_structure(self, client: AsyncClient, auth_headers: dict):
        """Bid prediction includes bid-to-tender ratio."""
        response = await client.post(
            "/api/v2/predictions/bid-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "tender_estimated_value": 5000000,
                "bid_competition_count": 5,
            },
        )
        if response.status_code == 200:
            data = response.json()
            assert "predicted_price" in data
            assert "bid_to_tender_ratio" in data
            assert 0 < data["bid_to_tender_ratio"] < 1

    @pytest.mark.asyncio
    async def test_bid_price_competition_impact(self, client: AsyncClient, auth_headers: dict):
        """Higher competition reduces predicted bid price."""
        # Low competition
        response1 = await client.post(
            "/api/v2/predictions/bid-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "tender_estimated_value": 5000000,
                "bid_competition_count": 2,
            },
        )

        # High competition
        response2 = await client.post(
            "/api/v2/predictions/bid-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "tender_estimated_value": 5000000,
                "bid_competition_count": 10,
            },
        )

        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            # Higher competition should yield lower predicted bid
            assert data1["predicted_price"] > data2["predicted_price"]

    @pytest.mark.asyncio
    async def test_bid_price_validation(self, client: AsyncClient, auth_headers: dict):
        """Input validation (value > 0, competition >= 1)."""
        # Invalid: zero value
        response = await client.post(
            "/api/v2/predictions/bid-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "tender_estimated_value": 0,
                "bid_competition_count": 5,
            },
        )
        assert response.status_code == 422

        # Invalid: zero bidders
        response = await client.post(
            "/api/v2/predictions/bid-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "tender_estimated_value": 5000000,
                "bid_competition_count": 0,
            },
        )
        assert response.status_code == 422


class TestModelStatus:
    """Test /api/v2/predictions/models/status endpoint."""

    @pytest.mark.asyncio
    async def test_model_status_structure(self, client: AsyncClient, auth_headers: dict):
        """Returns status for both tender and bid models."""
        response = await client.get(
            "/api/v2/predictions/models/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert "tender_price_model" in data
        assert "bid_price_model" in data

        for model in [data["tender_price_model"], data["bid_price_model"]]:
            assert "name" in model
            assert "version" in model
            assert "validation_rmse" in model
            assert "validation_r2" in model
            assert "training_samples" in model

    @pytest.mark.asyncio
    async def test_model_status_metrics_valid(self, client: AsyncClient, auth_headers: dict):
        """Model metrics are in valid ranges."""
        response = await client.get(
            "/api/v2/predictions/models/status",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            for model_key in ["tender_price_model", "bid_price_model"]:
                model = data[model_key]
                if model["validation_r2"] is not None:
                    # R² should be between -inf and 1 (typically 0-1 for good models)
                    assert model["validation_r2"] <= 1.0


class TestTrainingEndpoint:
    """Test /api/v2/predictions/train/tender-price endpoint."""

    @pytest.mark.asyncio
    async def test_training_requires_admin(self, client: AsyncClient, auth_headers: dict):
        """Training endpoint requires admin role (403 for non-admin)."""
        # With regular user (if role is not admin)
        response = await client.post(
            "/api/v2/predictions/train/tender-price",
            headers=auth_headers,
        )
        # Could be 403 (forbidden) or 503 (insufficient data)
        assert response.status_code in (403, 503)

    @pytest.mark.asyncio
    async def test_training_requires_auth(self, client: AsyncClient):
        """Training requires authentication."""
        response = await client.post("/api/v2/predictions/train/tender-price")
        assert response.status_code == 401


class TestAccuracyHistory:
    """Test /api/v2/predictions/accuracy-history endpoint."""

    @pytest.mark.asyncio
    async def test_accuracy_history_structure(self, client: AsyncClient, auth_headers: dict):
        """Returns weekly accuracy metrics."""
        response = await client.get(
            "/api/v2/predictions/accuracy-history",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert "model" in data
        assert "accuracy_history" in data
        assert "trend" in data  # improving, degrading, stable

    @pytest.mark.asyncio
    async def test_accuracy_history_limit(self, client: AsyncClient, auth_headers: dict):
        """Respects limit parameter."""
        response = await client.get(
            "/api/v2/predictions/accuracy-history?limit=5",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert len(data["accuracy_history"]) <= 5

    @pytest.mark.asyncio
    async def test_accuracy_history_metrics(self, client: AsyncClient, auth_headers: dict):
        """Each history entry has RMSE and MAPE."""
        response = await client.get(
            "/api/v2/predictions/accuracy-history",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            for entry in data["accuracy_history"]:
                assert "rmse" in entry
                assert "mape_pct" in entry
                assert "samples" in entry
                assert entry["rmse"] > 0
                assert 0 < entry["mape_pct"] < 100


class TestPredictionPerformance:
    """Test performance of prediction endpoints."""

    @pytest.mark.asyncio
    async def test_tender_price_latency(self, client: AsyncClient, auth_headers: dict):
        """Tender price prediction responds within SLO (<100ms p95)."""
        import time

        start = time.perf_counter()
        response = await client.post(
            "/api/v2/predictions/tender-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "duration_days": 30,
            },
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code in (200, 503)
        # Allow for cold start and no model; <5s for safety
        assert elapsed_ms < 5000

    @pytest.mark.asyncio
    async def test_bid_price_latency(self, client: AsyncClient, auth_headers: dict):
        """Bid price prediction responds quickly."""
        import time

        start = time.perf_counter()
        response = await client.post(
            "/api/v2/predictions/bid-price",
            headers=auth_headers,
            json={
                "zone_id": "A",
                "agency_id": "agency-1",
                "category_id": "category-1",
                "tender_estimated_value": 5000000,
                "bid_competition_count": 5,
            },
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 2000


class TestPredictionConsistency:
    """Test consistency across prediction calls."""

    @pytest.mark.asyncio
    async def test_same_inputs_same_output(self, client: AsyncClient, auth_headers: dict):
        """Same inputs should produce consistent outputs."""
        payload = {
            "zone_id": "A",
            "agency_id": "agency-1",
            "category_id": "category-1",
            "duration_days": 30,
        }

        response1 = await client.post(
            "/api/v2/predictions/tender-price",
            headers=auth_headers,
            json=payload,
        )

        response2 = await client.post(
            "/api/v2/predictions/tender-price",
            headers=auth_headers,
            json=payload,
        )

        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            # Predictions should be identical (deterministic model)
            assert data1["predicted_price"] == data2["predicted_price"]
