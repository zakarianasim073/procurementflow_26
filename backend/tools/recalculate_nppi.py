from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import get_sync_engine


RUNTIME_DIR = Path(__file__).resolve().parents[1] / "runtime" / "startup"


def main() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_sync_engine()
    with engine.begin() as conn:
        before = {
            "lifecycle_rows": conn.execute(text("SELECT COUNT(*) FROM procurement_lifecycle")).scalar() or 0,
            "lifecycle_with_estimate_award": conn.execute(text(
                "SELECT COUNT(*) FROM procurement_lifecycle WHERE estimated_cost_bdt > 0 AND award_amount_bdt > 0"
            )).scalar() or 0,
            "lifecycle_bad_nppi": conn.execute(text(
                "SELECT COUNT(*) FROM procurement_lifecycle "
                "WHERE estimated_cost_bdt > 0 AND award_amount_bdt > 0 "
                "AND (npp_ratio IS NULL OR npp_ratio <= 0 OR npp_ratio > 2)"
            )).scalar() or 0,
        }

        lifecycle_updated = conn.execute(text(
            "UPDATE procurement_lifecycle "
            "SET npp_ratio = ROUND((award_amount_bdt / NULLIF(estimated_cost_bdt, 0))::numeric, 6) "
            "WHERE estimated_cost_bdt > 0 AND award_amount_bdt > 0 "
            "AND (npp_ratio IS NULL OR npp_ratio <= 0 OR npp_ratio > 2 "
            "OR ABS(npp_ratio - (award_amount_bdt / NULLIF(estimated_cost_bdt, 0))) > 0.0005)"
        )).rowcount or 0

        award_updated = conn.execute(text(
            "UPDATE award_records_v2 "
            "SET npp_ratio = ROUND((amount_bdt / NULLIF(estimated_amount_bdt, 0))::numeric, 6), "
            "discount_pct = ROUND(((estimated_amount_bdt - amount_bdt) / NULLIF(estimated_amount_bdt, 0) * 100)::numeric, 4) "
            "WHERE estimated_amount_bdt > 0 AND amount_bdt > 0 "
            "AND (npp_ratio IS NULL OR npp_ratio <= 0 OR npp_ratio > 2 "
            "OR ABS(npp_ratio - (amount_bdt / NULLIF(estimated_amount_bdt, 0))) > 0.0005)"
        )).rowcount or 0

        after = {
            "lifecycle_bad_nppi": conn.execute(text(
                "SELECT COUNT(*) FROM procurement_lifecycle "
                "WHERE estimated_cost_bdt > 0 AND award_amount_bdt > 0 "
                "AND (npp_ratio IS NULL OR npp_ratio <= 0 OR npp_ratio > 2)"
            )).scalar() or 0,
            "credible_nppi_rows": conn.execute(text(
                "SELECT COUNT(*) FROM procurement_lifecycle "
                "WHERE estimated_cost_bdt > 0 AND award_amount_bdt > 0 "
                "AND npp_ratio > 0 AND npp_ratio <= 2"
            )).scalar() or 0,
            "avg_nppi": float(conn.execute(text(
                "SELECT COALESCE(AVG(npp_ratio), 0) FROM procurement_lifecycle "
                "WHERE estimated_cost_bdt > 0 AND award_amount_bdt > 0 "
                "AND npp_ratio > 0 AND npp_ratio <= 2"
            )).scalar() or 0),
        }

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "formula": "NPPI = award_amount_bdt / estimated_cost_bdt",
        "before": before,
        "updated": {
            "procurement_lifecycle": lifecycle_updated,
            "award_records_v2": award_updated,
        },
        "after": after,
    }
    out = RUNTIME_DIR / "nppi_recalculation.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
