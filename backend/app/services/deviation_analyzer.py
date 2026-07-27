"""Deviation Analyzer Service

Investigates BOQ vs APP estimate deviations.
Compares BOQ comparison output with APP records for the same tender
and identifies discrepancies in quantities, rates, or totals.

Used by agent-010-deviation-detector and the BOQ comparison pipeline.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text

from app.core.config import settings

logger = logging.getLogger(__name__)


def _sync_engine():
    url = settings.DATABASE_URL
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    return create_engine(url)


class DeviationAnalyzerService:
    """Analyze BOQ vs APP estimate deviations."""

    @classmethod
    def find_app_records(cls, tender_id: str) -> List[Dict[str, Any]]:
        """Find APP records for a given tender by title or tender_id."""
        engine = _sync_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, source_tender_id, procurement_tender_id,
                           estimated_cost_bdt, title, app_code, financial_year
                    FROM app_records
                    WHERE source_tender_id = :tid
                       OR title ILIKE :title
                    ORDER BY created_at DESC
                """),
                {"tid": tender_id, "title": f"%{tender_id}%"},
            )
            rows = []
            for r in result:
                rows.append({
                    "id": r.id,
                    "source_tender_id": r.source_tender_id,
                    "procurement_tender_id": r.procurement_tender_id,
                    "estimated_cost_bdt": r.estimated_cost_bdt,
                    "title": r.title,
                    "app_code": r.app_code,
                    "financial_year": r.financial_year,
                })
        engine.dispose()
        return rows

    @classmethod
    def analyze_boq_vs_app(
        cls,
        boq_items: List[Dict[str, Any]],
        tender_id: str,
    ) -> Dict[str, Any]:
        """Compare BOQ output with APP estimate for discrepancies."""
        app_records = cls.find_app_records(tender_id)
        total_sor = sum(
            (item.get("qty", 0) or 0) * (item.get("sor_rate", 0) or 0)
            for item in boq_items
        )
        total_quoted = sum(
            (item.get("qty", 0) or 0) * (item.get("rate", 0) or 0)
            for item in boq_items
        )
        matched = [x for x in boq_items if x.get("sor_rate") is not None]
        missing = [x for x in boq_items if x.get("sor_rate") is None]
        flagged = [x for x in boq_items if x.get("flag")]

        deviations = []
        for app in app_records:
            app_est = app.get("estimated_cost_bdt") or 0
            if app_est > 0:
                deviation = {
                    "app_id": app.get("id", "")[:8],
                    "app_code": app.get("app_code", ""),
                    "app_estimated_cost": app_est,
                    "boq_sor_total": total_sor,
                    "boq_quoted_total": total_quoted,
                    "diff_vs_app": total_quoted - app_est,
                    "pct_diff": round((total_quoted - app_est) / app_est * 100, 2) if app_est > 0 else 0,
                    "financial_year": app.get("financial_year", ""),
                }
                deviations.append(deviation)

        return {
            "tender_id": tender_id,
            "app_records_found": len(app_records),
            "boq_items": len(boq_items),
            "matched_sor": len(matched),
            "missing_sor": len(missing),
            "flagged_items": len(flagged),
            "total_sor_bdt": total_sor,
            "total_quoted_bdt": total_quoted,
            "deviations": deviations,
            "high_value_items": [
                {
                    "item_no": x.get("item_no"),
                    "code": x.get("code"),
                    "desc": x.get("desc", "")[:50],
                    "qty": x.get("qty"),
                    "rate": x.get("rate"),
                    "sor_rate": x.get("sor_rate"),
                    "flag": x.get("flag"),
                }
                for x in boq_items
                if (x.get("qty", 0) or 0) * (x.get("rate", 0) or 0) > 10_000_000
            ],
        }

    @classmethod
    def analyze_from_api_response(
        cls,
        api_response: Dict[str, Any],
        tender_id: str,
    ) -> Dict[str, Any]:
        """Convenience: analyze from a BOQ compare API response dict."""
        items = api_response.get("data", [])
        return cls.analyze_boq_vs_app(items, tender_id)


# ── Standalone CLI ────────────────────────────────────────────────────────────

def _cli():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.services.deviation_analyzer <tender_id>")
        sys.exit(1)
    tender_id = sys.argv[1]
    # Demo with empty BOQ items - real usage would pass actual items
    result = DeviationAnalyzerService.find_app_records(tender_id)
    print(f"APP records for {tender_id}: {len(result)}")
    for r in result[:5]:
        print(f"  {r['app_code']} est={r['estimated_cost_bdt']:,.0f} fy={r['financial_year']}")


if __name__ == "__main__":
    _cli()
