"""Historical calibration helpers for bid strategy and executive decisions."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import text

from app.db.database import get_sync_engine


MODEL_VERSION = "bid-decision-calibration-v1"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


class BidDecisionCalibrationService:
    """Calibrate decision heuristics against historical lifecycle outcomes."""

    def __init__(self) -> None:
        self.artifact_path = Path(__file__).resolve().parents[2] / "runtime" / "models" / "bid_decision_calibration.json"

    def _query_priors(self, agency: str = "", zone: str = "") -> Dict[str, Any]:
        where = [
            "discount_pct IS NOT NULL",
            "discount_pct BETWEEN -20 AND 40",
            "award_amount_bdt IS NOT NULL",
            "award_amount_bdt > 1000",
        ]
        params: Dict[str, Any] = {}
        if agency:
            where.append("agency_code ILIKE :agency")
            params["agency"] = f"%{agency}%"
        if zone:
            where.append("zone_name ILIKE :zone")
            params["zone"] = f"%{zone}%"
        # sql-ok: WHERE fragments from code constants; values bound
        sql = f"""
            SELECT
                count(*)::int AS sample_size,
                avg(discount_pct)::float AS avg_discount,
                percentile_cont(0.25) WITHIN GROUP (ORDER BY discount_pct)::float AS p25_discount,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY discount_pct)::float AS p50_discount,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY discount_pct)::float AS p75_discount,
                stddev_pop(discount_pct)::float AS std_discount,
                avg(npp_ratio)::float AS avg_npp
            FROM procurement_lifecycle
            WHERE {" AND ".join(where)}
        """
        try:
            with get_sync_engine().connect() as conn:
                row = conn.execute(text(sql), params).mappings().first()
                if row and row["sample_size"]:
                    return dict(row)
        except Exception:
            pass
        return {
            "sample_size": 0,
            "avg_discount": 5.5,
            "p25_discount": 3.5,
            "p50_discount": 5.5,
            "p75_discount": 8.0,
            "std_discount": 2.5,
            "avg_npp": 0.94,
        }

    def strategy_priors(self, agency: str, zone: str, estimate: float, risk_appetite: str) -> Dict[str, Any]:
        priors = self._query_priors(agency, zone)
        sample = int(priors.get("sample_size") or 0)
        p25 = _safe_float(priors.get("p25_discount"), 3.5)
        p50 = _safe_float(priors.get("p50_discount"), 5.5)
        p75 = _safe_float(priors.get("p75_discount"), 8.0)
        std = max(_safe_float(priors.get("std_discount"), 2.5), 1.0)
        avg_discount = _safe_float(priors.get("avg_discount"), p50)
        nppi_discount = max(0.0, min(40.0, (1.0 - _safe_float(priors.get("avg_npp"), 0.94)) * 100.0))
        weighted_average = max(1.0, min(25.0, (0.5 * nppi_discount) + (0.3 * p50) + (0.2 * avg_discount)))
        confidence = "high" if sample >= 500 else "medium" if sample >= 100 else "low"
        strategies = {
            "Conservative": max(1.0, weighted_average - 2.0),
            "Balanced": weighted_average,
            "Aggressive": min(25.0, weighted_average + 2.0),
        }
        return {
            "model_version": MODEL_VERSION,
            "trained": sample >= 100,
            "sample_size": sample,
            "confidence": confidence,
            "risk_appetite": risk_appetite,
            "historical_discount": {
                "p25": round(p25, 3),
                "p50": round(p50, 3),
                "p75": round(p75, 3),
                "std": round(std, 3),
                "avg": round(avg_discount, 3),
                "nppi_discount": round(nppi_discount, 3),
                "weighted_average": round(weighted_average, 3),
            },
            "strategy_discounts": strategies,
            "feature_snapshot": {
                "agency": agency,
                "zone": zone,
                "estimate": estimate,
                "risk_appetite": risk_appetite,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def calibrated_win_probability(self, discount: float, priors: Dict[str, Any], competitor_count: int) -> int:
        hist = priors.get("historical_discount", {})
        p50 = _safe_float(hist.get("p50"), 5.5)
        std = max(_safe_float(hist.get("std"), 2.5), 1.0)
        comp = max(int(competitor_count or 5), 1)
        base = 100.0 / comp
        z = (discount - p50) / std
        uplift = 28.0 / (1.0 + math.exp(-z)) - 14.0
        return int(max(5, min(90, round(base + uplift))))

    def executive_policy(self, features: Dict[str, Any]) -> Dict[str, Any]:
        win_prob = _safe_float(features.get("win_probability"))
        margin = _safe_float(features.get("expected_margin"))
        capacity = bool(features.get("capacity_available", True))
        degraded = bool(features.get("degraded_mode", False))
        evidence = _safe_float(features.get("evidence_score"), 0.5)
        score = (win_prob * 0.45) + (margin * 2.0) + (15.0 if capacity else 0.0)
        threshold = 58.0
        if degraded:
            threshold += 5.0
        if evidence < 0.45:
            threshold += 5.0
        decision = "BID" if score >= threshold else "NO-BID"
        confidence = "high" if evidence >= 0.75 and abs(score - threshold) >= 10 else "medium" if evidence >= 0.5 else "low"
        return {
            "model_version": MODEL_VERSION,
            "decision": decision,
            "score": round(score, 3),
            "threshold": round(threshold, 3),
            "confidence_level": confidence,
            "feature_snapshot": dict(features),
            "explanation": {
                "win_probability_weight": 0.45,
                "margin_weight": 2.0,
                "capacity_bonus": 15.0 if capacity else 0.0,
                "degraded_penalty": 5.0 if degraded else 0.0,
                "low_evidence_penalty": 5.0 if evidence < 0.45 else 0.0,
            },
        }

    def persist_artifact(self, payload: Dict[str, Any]) -> None:
        try:
            self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
            existing: List[Dict[str, Any]] = []
            if self.artifact_path.exists():
                existing = json.loads(self.artifact_path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = [existing]
            existing.append(payload)
            self.artifact_path.write_text(json.dumps(existing[-500:], indent=2, default=str), encoding="utf-8")
        except Exception:
            pass


decision_calibration_service = BidDecisionCalibrationService()
