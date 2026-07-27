from __future__ import annotations

from app.agents.competitor.bid_position_optimizer import BidPositionOptimizerAgent
from app.agents.competitor.competitor_intelligence import CompetitorIntelligenceAgent
from app.agents.competitor.competitor_pricing_predictor import CompetitorPricingPredictorAgent
from app.agents.competitor.moat_slt_analyzer import MoatSLTAnalyzerAgent
from app.agents.competitor.syndicate_radar import SyndicateRadarAgent
from app.agents.competitor.win_probability import WinProbabilityAgent
from app.agents.core.regime import (
    REGIME_PPR2025,
    build_regime_aware_query,
    get_slt_status,
    get_thresholds,
)
from app.agents.evaluation.lert_prediction import LERTPredictionAgent
from app.agents.evaluation.ppr_evaluation import Finding, PPREvaluationAgent


def test_ppr2025_agent_versions_match_roadmap():
    assert PPREvaluationAgent.version.startswith("4.")
    assert LERTPredictionAgent.version.startswith("4.")
    assert BidPositionOptimizerAgent.version.startswith("3.")
    assert CompetitorIntelligenceAgent.version.startswith("3.")
    assert CompetitorPricingPredictorAgent.version.startswith("4.")
    assert MoatSLTAnalyzerAgent.version.startswith("2.")
    assert SyndicateRadarAgent.version.startswith("2.")
    assert WinProbabilityAgent.version.startswith("4.")


def test_regime_helpers_expose_ppr2025_slt_alt_contract():
    thresholds = get_thresholds(REGIME_PPR2025)

    assert "slt_threshold" in thresholds
    assert "alt_threshold" in thresholds
    assert get_slt_status(59, 100, REGIME_PPR2025)["status"] == "ALT"
    assert "2025-09-28" in build_regime_aware_query("SELECT * FROM tenders t", regime=REGIME_PPR2025)


def test_ppr_finding_carries_regime_field():
    finding = Finding(regime=REGIME_PPR2025)

    assert finding.regime == REGIME_PPR2025
