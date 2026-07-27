from __future__ import annotations

import pytest

from app.agents.competitor.competitor_pricing_predictor import CompetitorPricingPredictorAgent
from app.services.decision_calibration import decision_calibration_service


def test_strategy_priors_use_nppi_weighted_average(monkeypatch):
    monkeypatch.setattr(
        decision_calibration_service,
        "_query_priors",
        lambda agency, zone: {
            "sample_size": 250,
            "avg_discount": 8.0,
            "p25_discount": 6.0,
            "p50_discount": 10.0,
            "p75_discount": 14.0,
            "std_discount": 3.0,
            "avg_npp": 0.90,
        },
    )

    priors = decision_calibration_service.strategy_priors("BWDB", "Khulna", 50_000_000, "moderate")

    assert priors["historical_discount"]["weighted_average"] == 9.6
    assert priors["strategy_discounts"]["Conservative"] == pytest.approx(7.6)
    assert priors["strategy_discounts"]["Balanced"] == pytest.approx(9.6)
    assert priors["strategy_discounts"]["Aggressive"] == pytest.approx(11.6)


def test_competitor_prediction_is_deterministic():
    agent = CompetitorPricingPredictorAgent()
    competitor = {
        "name": "ABC Construction",
        "avg_discount": 7.5,
        "discount_stddev": 1.2,
        "win_rate": 12,
        "total_wins": 20,
        "preferred_agency": "BWDB",
    }

    first = agent._predict_single_competitor(competitor, 100_000_000)
    second = agent._predict_single_competitor(competitor, 100_000_000)

    assert first == second
    assert first["prediction_method"] == "statistical_deterministic"
    assert first["expected_bid"] == pytest.approx(92_500_000)


@pytest.mark.asyncio
async def test_app_noa_facade_signature_accepts_agency_and_limit():
    from app.services.app_noa_service import APPNOAMatchingService

    service = APPNOAMatchingService.__new__(APPNOAMatchingService)
    assert hasattr(service, "list_awards_for_agent")

    # Signature regression guard: IntelligenceDataService passes (agency, limit).
    import inspect

    params = list(inspect.signature(APPNOAMatchingService.list_awards_for_agent).parameters)
    assert params[:3] == ["self", "agency", "limit"]
