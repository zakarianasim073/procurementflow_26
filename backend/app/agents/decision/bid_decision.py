"""
Agent 39 — Bid/No-Bid Engine
Phase 2: Decision Intelligence Engine

Composite Bid Score (0-100):
  35% Win Probability
  25% Margin
  15% Competition
  10% Capacity (estimated)
  10% Cashflow proxy (tender size vs avg)
   5% Strategic Value

Decision thresholds:
  ≥ 75  → BID (AGGRESSIVE_BID if WP ≥ 70)
  60-74 → REVIEW
  < 60  → NO-BID
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.db.database import get_sync_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BidNoBidAgent(BaseAgent):
    agent_id = "agent-039-bid-no-bid"
    agent_name = "Bid/No-Bid Engine"
    description = "Decision engine: recommends BID or NO-BID using composite bid score (WP×35 + Margin×25 + Competition×15 + Capacity×10 + Cashflow×10 + Strategic×5)."
    dependencies = ["agent-016-win-probability", "agent-017-bid-position-optimizer", "agent-022-executive-decision"]
    version = "2.0.0"

    AGENCY_BLACKLIST: List[str] = []

    # Score thresholds
    SCORE_BID = 75
    SCORE_REVIEW = 60

    # Legacy per-factor thresholds (still checked for factor table)
    MIN_PROFIT_MARGIN = 12.0
    MIN_WIN_PROB = 40.0

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        tender_id = context.get("tender_id", "")
        agency = context.get("agency", "")
        estimate = float(context.get("estimate", context.get("estimated_amount", 0)) or 0)
        company = context.get("company_profile", context.get("company", {}))

        # Gather intelligence from other agents
        win_data = await self._get_win_probability(tender_id, context)
        bid_data = await self._get_bid_position(tender_id, context)
        exec_data = await self._get_executive_decision(tender_id, context)

        # Check blacklist
        if agency in self.AGENCY_BLACKLIST:
            result = self._decision_result(
                decision="NO-BID", score=0,
                win_prob=0, margin=0, agency=agency,
                reasons=["Agency blacklisted"],
                bid_data=bid_data,
            )
            return AgentResult(status=AgentStatus.SUCCESS, output=result)

        # ── Extract sub-signals ─────────────────────────────────────────
        win_prob = float(win_data.get("probability", 50) or 50)

        margin = 10.0
        if bid_data:
            recommendation = bid_data.get("recommendation", {}) or {}
            ranges = bid_data.get("ranges", []) or []
            fallback_range = ranges[1] if len(ranges) > 1 and isinstance(ranges[1], dict) else {}
            margin = float(
                recommendation.get("estimated_margin_pct")
                if isinstance(recommendation, dict) and recommendation.get("estimated_margin_pct") is not None
                else fallback_range.get("estimated_margin_pct", 10)
            )

        competition_score = self._score_competition(bid_data)
        capacity_score = self._score_capacity(company, estimate)
        cashflow_score = self._score_cashflow(estimate)
        strategic_score = self._score_strategic(agency, company)

        # ── Composite bid score ─────────────────────────────────────────
        bid_score = self._compute_bid_score(
            win_prob, margin, competition_score, capacity_score, cashflow_score, strategic_score
        )

        decision, reasons = self._decide_from_score(bid_score, win_prob, margin, agency)
        confidence = self._compute_confidence(win_data, bid_data, exec_data)

        result = {
            "decision": decision,
            "bid_score": round(bid_score, 1),
            "confidence": confidence,
            "win_probability": win_prob,
            "expected_margin_pct": round(margin, 1),
            "estimated_bid_amount": bid_data.get("recommendation", {}).get("bid_amount", 0) if bid_data else 0,
            "reasons": reasons,
            "score_breakdown": {
                "win_probability": round(win_prob * 0.35, 1),
                "margin": round(min(margin / 20.0 * 100 * 0.25, 25), 1),
                "competition": round(competition_score * 0.15, 1),
                "capacity": round(capacity_score * 0.10, 1),
                "cashflow": round(cashflow_score * 0.10, 1),
                "strategic": round(strategic_score * 0.05, 1),
            },
            "factors": [
                {"name": "Win Probability", "value": f"{win_prob}%", "threshold": f">{self.MIN_WIN_PROB}%", "pass": win_prob >= self.MIN_WIN_PROB},
                {"name": "Expected Margin", "value": f"{margin:.1f}%", "threshold": f">{self.MIN_PROFIT_MARGIN}%", "pass": margin >= self.MIN_PROFIT_MARGIN},
                {"name": "Competition Score", "value": f"{competition_score:.0f}/100", "threshold": ">50", "pass": competition_score >= 50},
                {"name": "Agency Risk", "value": agency, "pass": agency not in self.AGENCY_BLACKLIST},
            ],
            "version": "2.0",
        }

        await self.share_knowledge(
            entry_type="bid_decision", tender_id=tender_id,
            data=result,
            summary=f"{decision}: score={bid_score:.0f}/100, WP={win_prob}%, margin={margin:.1f}%",
            tags=["bid-decision", decision],
        )

        return AgentResult(status=AgentStatus.SUCCESS, output=result)

    # ── Scoring helpers ─────────────────────────────────────────────────

    def _compute_bid_score(
        self,
        win_prob: float, margin: float,
        competition: float, capacity: float, cashflow: float, strategic: float,
    ) -> float:
        """
        Bid Score =
          35% × Win Probability (0-100)
          25% × Margin score (capped at 20% margin → 100 pts)
          15% × Competition score (0-100)
          10% × Capacity score (0-100)
          10% × Cashflow score (0-100)
           5% × Strategic score (0-100)
        """
        margin_score = min(100.0, (margin / 20.0) * 100.0)
        return (
            0.35 * win_prob
            + 0.25 * margin_score
            + 0.15 * competition
            + 0.10 * capacity
            + 0.10 * cashflow
            + 0.05 * strategic
        )

    def _score_competition(self, bid_data: Optional[Dict]) -> float:
        """Derive competition score from market context in bid_data."""
        if not bid_data:
            return 50.0
        market = bid_data.get("market_context", {}) or {}
        level = (market.get("competition_level") or "Medium").lower()
        if level == "low":
            return 80.0
        if level == "high":
            return 30.0
        return 55.0

    def _score_capacity(self, company: Dict, estimate: float) -> float:
        """Estimate capacity score based on available company info."""
        if not company:
            return 60.0  # neutral default
        experience = float(company.get("experience_years", company.get("years_in_business", 5)) or 5)
        # More experience → higher capacity score
        score = min(100.0, 40.0 + experience * 3.0)
        # Large tenders with new companies → penalise
        if estimate > 100_000_000 and experience < 5:
            score = max(20.0, score - 20.0)
        return round(score, 1)

    def _score_cashflow(self, estimate: float) -> float:
        """Proxy cashflow risk from tender size: larger = more working capital needed."""
        if estimate <= 0:
            return 60.0
        crore = estimate / 10_000_000
        if crore <= 1:
            return 90.0   # Small tender, low cashflow risk
        if crore <= 5:
            return 75.0
        if crore <= 20:
            return 60.0
        if crore <= 100:
            return 45.0
        return 30.0       # Very large tender, high cashflow demand

    def _score_strategic(self, agency: str, company: Dict) -> float:
        """Strategic value: 70 by default, 100 if agency is a preferred client."""
        preferred = company.get("preferred_agencies", []) or []
        if agency and agency in preferred:
            return 100.0
        return 70.0

    def _decide_from_score(self, score: float, win_prob: float, margin: float, agency: str):
        reasons = []
        if score >= self.SCORE_BID:
            if win_prob >= 70:
                decision = "AGGRESSIVE_BID"
                reasons.append(f"Composite bid score {score:.0f}/100 — strong position")
                reasons.append(f"Win probability {win_prob:.0f}% is high — bid aggressively")
            else:
                decision = "BID"
                reasons.append(f"Composite bid score {score:.0f}/100 exceeds BID threshold ({self.SCORE_BID})")
                reasons.append(f"Win probability {win_prob:.0f}% and margin {margin:.1f}% are acceptable")
        elif score >= self.SCORE_REVIEW:
            decision = "REVIEW"
            reasons.append(f"Composite bid score {score:.0f}/100 — marginal, requires senior review")
            if win_prob < self.MIN_WIN_PROB:
                reasons.append(f"Win probability {win_prob:.0f}% below threshold {self.MIN_WIN_PROB}%")
            if margin < self.MIN_PROFIT_MARGIN:
                reasons.append(f"Expected margin {margin:.1f}% below threshold {self.MIN_PROFIT_MARGIN}%")
        else:
            decision = "NO-BID"
            reasons.append(f"Composite bid score {score:.0f}/100 — below NO-BID threshold ({self.SCORE_REVIEW})")
            reasons.append(f"Win probability {win_prob:.0f}% and/or margin {margin:.1f}% insufficient")
        return decision, reasons

    def _decision_result(self, *, decision, score, win_prob, margin, agency, reasons, bid_data) -> Dict:
        return {
            "decision": decision,
            "bid_score": score,
            "confidence": "Low",
            "win_probability": win_prob,
            "expected_margin_pct": margin,
            "estimated_bid_amount": 0,
            "reasons": reasons,
            "score_breakdown": {},
            "factors": [{"name": "Agency Risk", "value": agency, "pass": False}],
            "version": "2.0",
        }

    # ── Agent calls ─────────────────────────────────────────────────────

    async def _get_win_probability(self, tender_id: str, ctx: Dict) -> Dict:
        if self.brain and tender_id:
            try:
                r = await self.ask_agent("agent-016-win-probability", "compute", ctx)
                return r or {}
            except Exception:
                pass
        return {}

    async def _get_bid_position(self, tender_id: str, ctx: Dict) -> Dict:
        if self.brain and tender_id:
            try:
                r = await self.ask_agent("agent-017-bid-position-optimizer", "compute", ctx)
                return r or {}
            except Exception:
                pass
        return {}

    async def _get_executive_decision(self, tender_id: str, ctx: Dict) -> Dict:
        if self.brain and tender_id:
            try:
                r = await self.ask_agent("agent-022-executive-decision", "evaluate", ctx)
                return r or {}
            except Exception:
                pass
        return {}

    def _compute_confidence(self, win: Dict, bid: Dict, exec_: Dict) -> str:
        score = 0
        if win:
            score += 40
        if bid:
            score += 30
        if exec_:
            score += 30
        return "High" if score >= 70 else "Medium" if score >= 40 else "Low"
