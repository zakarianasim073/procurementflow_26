"""
Agent 12 — Market Rate Intelligence Agent
Analyzes actual SOR rates vs market prices from the material_prices table.
No hardcoded data — all rates come from PostgreSQL (sor_rates + material_prices).
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.db.database import get_sync_engine

logger = logging.getLogger(__name__)


class MarketRateIntelligenceAgent(BaseAgent):
    agent_id = "agent-012-market-rate-intelligence"
    agent_name = "Market Rate Intelligence Agent"
    description = "Compares actual SOR schedule rates with market prices from material_prices table. No hardcoded data."
    dependencies: List[str] = ["agent-011-rate-analysis"]
    version = "3.0.0"

    ZONE_COLUMN = {"A": "zone_a", "B": "zone_b", "C": "zone_c", "D": "zone_d"}

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        agency = context.get("agency", "BWDB")
        zone = context.get("zone", "A")
        if isinstance(zone, dict):
            zone = str(zone.get(agency, zone.get("BWDB", "A")))
        zone = str(zone or "A")[:1].upper()
        limit = int(context.get("limit", 80))

        market_rates = await self._analyze_market_rates(agency, zone, limit)
        return AgentResult(
            agent_id=self.agent_id, agent_name=self.agent_name,
            status=AgentStatus.SUCCESS, output=market_rates,
        )

    async def _analyze_market_rates(self, agency: str, zone: str, limit: int) -> Dict:
        """Compare SOR rates with material_prices from PostgreSQL."""
        zone_col = self.ZONE_COLUMN.get(zone, "zone_a")
        engine = get_sync_engine()

        # ── Fetch SOR rates ──────────────────────────────────────────
        with engine.connect() as conn:
            # sql-ok: zone column from ZONE_COLUMN allowlist; values bound
            sor_rows = conn.execute(text(f"""
                SELECT code, description, unit, {zone_col} AS sor_rate
                FROM sor_rates
                WHERE agency = :agency
                  AND is_active = true
                  AND {zone_col} > 0
                ORDER BY {zone_col} DESC
                LIMIT :limit
            """), {"agency": agency, "limit": limit}).fetchall()

            # Fetch market prices
            market_rows = conn.execute(text("""
                SELECT category, zone, AVG(price_bdt) AS avg_price,
                       COUNT(*) AS sample_count
                FROM material_prices
                WHERE price_bdt > 0
                GROUP BY category, zone
            """)).fetchall()

        market_by_cat_zone: Dict[str, Dict] = {}
        for row in market_rows:
            key = f"{row.category}|{row.zone}"
            market_by_cat_zone[key] = {
                "avg": float(row.avg_price),
                "samples": int(row.sample_count),
            }

        # ── Classify SOR items and compare ───────────────────────────
        from app.agents.discovery.material_margin_analyzer import MaterialMarginAnalyzerAgent
        classifier = MaterialMarginAnalyzerAgent()

        items = []
        flagged_items = []
        category_stats: Dict[str, Dict] = {}
        total_matched = 0

        for row in sor_rows:
            code, desc, unit, sor_rate = row
            if not desc:
                continue
            sor_rate_f = float(sor_rate or 0)
            category = classifier._classify_material(desc)
            if not category:
                continue

            # Try zone-specific market price, fall back to any zone
            mkt = market_by_cat_zone.get(f"{category}|{zone}") or market_by_cat_zone.get(f"{category}|")
            if not mkt:
                continue

            variance_pct = ((sor_rate_f - mkt["avg"]) / max(mkt["avg"], 1)) * 100
            item = {
                "code": code,
                "description": desc[:120],
                "unit": unit,
                "category": category,
                "sor_rate": round(sor_rate_f, 2),
                "market_price": round(mkt["avg"], 2),
                "variance_pct": round(variance_pct, 1),
                "samples": mkt["samples"],
                "flag": "ABOVE_MARKET" if variance_pct > 10
                    else "BELOW_MARKET" if variance_pct < -10
                    else "AT_PAR",
            }
            items.append(item)
            total_matched += 1

            if abs(variance_pct) > 15:
                flagged_items.append(item)

            # Aggregate by category
            if category not in category_stats:
                category_stats[category] = {
                    "category": category,
                    "items": [],
                    "total_variance": 0.0,
                    "sor_total": 0.0,
                    "market_total": 0.0,
                }
            cat = category_stats[category]
            cat["items"].append(item)
            cat["total_variance"] += abs(variance_pct)
            cat["sor_total"] += sor_rate_f
            cat["market_total"] += mkt["avg"]

        # ── Compute category summaries ───────────────────────────────
        for cat_name, cat in category_stats.items():
            n = max(len(cat["items"]), 1)
            cat["avg_variance_pct"] = round(cat["total_variance"] / n, 1)
            cat["count"] = len(cat["items"])
            cat["avg_sor"] = round(cat["sor_total"] / n, 2)
            cat["avg_market"] = round(cat["market_total"] / n, 2)
            del cat["items"]
            del cat["total_variance"]
            del cat["sor_total"]
            del cat["market_total"]

        # ── Overall assessment ───────────────────────────────────────
        if items:
            overall_variance = sum(abs(i["variance_pct"]) for i in items) / len(items)
        else:
            overall_variance = 0.0

        return {
            "zone": zone,
            "agency": agency,
            "total_sor_items": len(sor_rows),
            "matched_to_market": total_matched,
            "overall_variance_pct": round(overall_variance, 1),
            "overall_assessment": (
                "SOR rates are significantly above market — good margins possible"
                if overall_variance > 10
                else "SOR rates are moderately above market"
                if overall_variance > 5
                else "SOR rates align with market"
                if overall_variance > -5
                else "SOR rates are below market — be cautious with bidding"
            ),
            "categories": {k: v for k, v in sorted(category_stats.items())},
            "flagged_items": flagged_items[:20],
            "recommendations": [
                f"Category with highest variance: "
                f"{max(category_stats.items(), key=lambda x: x[1]['avg_variance_pct'])[0]}"
                if category_stats else "No data to recommend",
                f"{len(flagged_items)} items flagged with >15% variance",
                "Use Agent 047 (Material Margin Analyzer) for item-level margin breakdown",
            ],
        }