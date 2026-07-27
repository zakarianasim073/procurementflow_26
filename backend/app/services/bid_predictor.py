"""
Bid Predictor Service - Predicts winning bids using real historical patterns from discount_patterns table.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEFAULT_PATTERN = {"avg_npp": 5.5, "stddev_npp": 2.0, "min_npp": 1.0, "max_npp": 10.0, "sample_size": 0}


class BidPredictor:
    """Predict bid outcomes using real discount_patterns data from the DB."""

    def __init__(self):
        self._patterns_cache: Dict[str, dict] = {}
        self._cache_loaded = False

    async def _load_patterns(self, db: AsyncSession) -> None:
        """Load discount patterns from the database into cache."""
        result = await db.execute(text("""
            SELECT agency_code, zone_name, sample_size, avg_npp, min_npp, max_npp, median_npp, stddev_npp
            FROM discount_patterns
            WHERE sample_size > 0
            ORDER BY sample_size DESC
        """))
        rows = result.mappings().all()
        self._patterns_cache = {}
        for row in rows:
            key = row["agency_code"].upper()
            # Keep the pattern with the largest sample_size per agency
            if key not in self._patterns_cache or row["sample_size"] > self._patterns_cache[key]["sample_size"]:
                self._patterns_cache[key] = {
                    "avg_npp": row["avg_npp"] or DEFAULT_PATTERN["avg_npp"],
                    "stddev_npp": row["stddev_npp"] or DEFAULT_PATTERN["stddev_npp"],
                    "min_npp": row["min_npp"] or DEFAULT_PATTERN["min_npp"],
                    "max_npp": row["max_npp"] or DEFAULT_PATTERN["max_npp"],
                    "sample_size": row["sample_size"] or 0,
                }
        self._cache_loaded = True
        logger.info("Loaded %d discount patterns from DB", len(self._patterns_cache))

    async def predict(self, tender_id: str = "", agency: str = "",
                      estimate: float = 0.0, work_type: str = "Civil Works",
                      num_bidders: int = 7, db: Optional[AsyncSession] = None) -> Dict:
        """
        Predict winning bid range and probability using real discount_patterns data.
        Falls back to defaults when no DB session or patterns are available.
        """
        if db is not None:
            try:
                if not self._cache_loaded:
                    await self._load_patterns(db)
                pattern = self._patterns_cache.get(agency.upper(), DEFAULT_PATTERN)
            except Exception as e:
                logger.warning("Failed to load discount patterns from DB: %s", e)
                pattern = DEFAULT_PATTERN
        else:
            pattern = DEFAULT_PATTERN

        expected_discount = pattern["avg_npp"]
        low_discount = max(pattern["min_npp"], expected_discount - pattern["stddev_npp"])
        high_discount = min(pattern["max_npp"], expected_discount + pattern["stddev_npp"])

        competition_factor = 1.0 + max(0, (num_bidders - 5)) * 0.02
        adjusted_expected_discount = expected_discount * competition_factor
        adjusted_low_discount = low_discount * competition_factor
        adjusted_high_discount = high_discount * competition_factor

        winning_price_low = estimate * (1 - adjusted_high_discount / 100)
        winning_price_high = estimate * (1 - adjusted_low_discount / 100)
        expected_price = estimate * (1 - adjusted_expected_discount / 100)

        return {
            "tender_id": tender_id,
            "agency": agency,
            "estimate": estimate,
            "work_type": work_type,
            "predicted": {
                "expected_discount_pct": round(adjusted_expected_discount, 2),
                "discount_range": [
                    round(adjusted_low_discount, 2),
                    round(adjusted_high_discount, 2),
                ],
                "expected_winning_price": round(expected_price, 2),
                "price_range": [
                    round(winning_price_low, 2),
                    round(winning_price_high, 2),
                ],
            },
            "confidence": "medium" if num_bidders >= 5 else "low",
            "num_bidders_estimated": num_bidders,
            "model": "discount_patterns_v2",
            "sample_size": pattern["sample_size"],
        }


bid_predictor = BidPredictor()
