"""Rate Analysis API — element-wise breakdown with market prices & profit margin."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_async_session
from app.schemas.response_models import CompositionsResponse, MarketPricesResponse
from app.services.boq_processor import BOQProcessor
from app.services.boq_excel_generator import generate_boq_excel
from app.services.rate_analysis_engine import analyze_boq_items

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rate-analysis", tags=["rate-analysis"])


@router.post("/from-compare")
async def rate_analysis_from_compare(
    boq_file_id: str = Form(...),
    sor_agency: str = Form("BWDB"),
    zone: Optional[str] = Form(None),
    tender_info: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_session),
):
    """Run BOQ comparison THEN element-wise rate analysis with market prices & profit margin.

    Same inputs as /api/boq/compare, but also returns element-level breakdown
    and generates a 6-tab Excel with the Rate Analysis tab.
    """
    # Resolve zone
    resolved_zone = zone
    if zone and zone.startswith("{"):
        try:
            resolved_zone = json.loads(zone)
        except Exception:
            resolved_zone = zone

    tender_info_dict = {}
    if tender_info:
        try:
            tender_info_dict = json.loads(tender_info)
        except Exception:
            pass

    # Find BOQ file
    upload_dir = Path(settings.BASE_DIR) / "uploads"
    boq_files = list(upload_dir.glob(f"{boq_file_id}.*"))
    if not boq_files:
        raise HTTPException(status_code=404, detail=f"BOQ file {boq_file_id} not found")

    boq_path = str(boq_files[0])

    # Step 1: Run BOQ comparison
    try:
        processor = BOQProcessor()
        comparison = await processor.compare(
            boq_path=boq_path,
            sor_agency=sor_agency,
            zone=resolved_zone,
            sor_service=None,
            tender_info=tender_info_dict,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BOQ comparison failed: {str(e)}")

    if not comparison.get("success"):
        raise HTTPException(status_code=500, detail=comparison.get("error", "BOQ comparison failed"))

    data = comparison["data"]
    summary = comparison["summary"]
    flagged = comparison.get("flagged", [])

    # Step 2: Build enriched items for rate analysis
    enriched = []
    for item in data:
        enriched.append({
            "item_no": item.get("item_no", ""),
            "code": item.get("code", ""),
            "description": item.get("desc", "") or item.get("description", ""),
            "unit": item.get("unit", ""),
            "quantity": item.get("qty", 0),
            "quoted_rate": item.get("rate"),
            "sor_rate": item.get("sor_rate"),
            "match_type": item.get("match_type", ""),
        })

    zone_str = zone if isinstance(zone, str) else "A"
    analyzed = analyze_boq_items(enriched, zone_str)

    # Step 3: Build tender info for Excel
    app_est = tender_info_dict.get("estimated_cost_app") or summary.get("estimated_cost_app")
    info = {
        "tender_id": tender_info_dict.get("tender_id", "N/A"),
        "package_no": tender_info_dict.get("package_no", ""),
        "package_description": tender_info_dict.get("title", tender_info_dict.get("brief", "")),
        "procuring_entity": tender_info_dict.get("procuring_entity", tender_info_dict.get("organization", sor_agency)),
        "location": tender_info_dict.get("location", tender_info_dict.get("district", "")),
        "district": tender_info_dict.get("district", tender_info_dict.get("location", "")),
        "sor_agency": f"{sor_agency} Schedule of Rates",
        "estimated_cost_app": app_est,
        "total_sor": summary.get("total_sor", 0),
        "total_quoted": summary.get("total_quoted", 0),
        "saving": summary.get("total_sor", 0) - summary.get("total_quoted", 0),
        "discount_pct": summary.get("discount_pct", 0),
        "tender_security_text": tender_info_dict.get("tender_security_text", ""),
        "tender_close_datetime": tender_info_dict.get("tender_close_datetime", ""),
        "work_period": tender_info_dict.get("work_period", ""),
        "invitation_ref": tender_info_dict.get("invitation_ref", ""),
    }

    # Step 4: Generate 6-tab Excel
    excel_items = []
    for a in analyzed:
        ra = a.get("rate_analysis", {})
        excel_items.append({
            "item_no": a.get("item_no", ""),
            "code": a.get("code", ""),
            "description": a.get("description", ""),
            "unit": a.get("unit", ""),
            "quantity": a.get("quantity", 0),
            "rate": a.get("quoted_rate"),
            "quoted_rate": a.get("quoted_rate"),
            "sor_rate": a.get("sor_rate"),
            "match_type": a.get("match_type", ""),
            "sor_source": a.get("code", ""),
            "work_type": a.get("work_type", ""),
        })

    output_dir = Path(settings.BASE_DIR) / "outputs" / "rate_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    tid = info["tender_id"] or "unknown"
    output_path = str(output_dir / f"BOQ_6Tab_RateAnalysis_{tid}.xlsx")

    try:
        generate_boq_excel(info, excel_items, zone=zone_str, output_path=output_path)
    except Exception as e:
        logger.warning(f"Excel generation failed: {e}")
        output_path = None

    # Step 5: Build profit summary
    items_with_analysis = [a for a in analyzed if a.get("rate_analysis", {}).get("has_composition")]
    margins = []
    for a in items_with_analysis:
        ra = a.get("rate_analysis", {})
        m = ra.get("profit_margin_vs_market")
        if m is not None:
            margins.append(m)

    profit_summary = {
        "items_with_composition": len(items_with_analysis),
        "items_total": len(analyzed),
        "profit_margins": {
            "avg_pct": round(sum(margins) / len(margins), 2) if margins else None,
            "min_pct": min(margins) if margins else None,
            "max_pct": max(margins) if margins else None,
            "safe_gt_15": sum(1 for m in margins if m > 15),
            "tight_5_to_15": sum(1 for m in margins if 5 <= m <= 15),
            "at_risk_0_to_5": sum(1 for m in margins if 0 < m < 5),
            "loss_le_0": sum(1 for m in margins if m <= 0),
        },
    }

    return JSONResponse({
        "success": True,
        "tender_id": info["tender_id"],
        "zone": zone_str,
        "comparison": {
            "total_items": len(data),
            "total_sor": round(summary.get("total_sor", 0), 2),
            "total_quoted": round(summary.get("total_quoted", 0), 2),
            "discount_pct": round(summary.get("discount_pct", 0) * 100, 2),
            "flagged_items": len(flagged),
        },
        "rate_analysis": {
            "items_with_composition": len(items_with_analysis),
            "items_without_composition": len(analyzed) - len(items_with_analysis),
            "profit_summary": profit_summary["profit_margins"],
        },
        "excel_path": output_path,
        "details": [
            {
                "sor_code": a.get("code", ""),
                "description": a.get("description", "")[:60],
                "quoted_rate": a.get("quoted_rate"),
                "sor_rate": a.get("sor_rate"),
                "market_cost_per_unit": a["rate_analysis"].get("total_market_cost_per_unit"),
                "profit_margin_pct": a["rate_analysis"].get("profit_margin_vs_market"),
                "sor_vs_market_pct": a["rate_analysis"].get("sor_vs_market_pct"),
                "elements": [
                    {
                        "sub_desc": e["sub_desc"][:30],
                        "component": e["component"],
                        "market_cost": e["market_cost_per_work_unit"],
                    }
                    for e in a["rate_analysis"].get("elements", [])
                    if e.get("market_cost_per_work_unit") is not None
                ],
            }
            for a in items_with_analysis[:20]
        ],
    }, ensure_ascii=False)


@router.post("/analyze-items")
async def analyze_items(
    items: str = Form(...),
    zone: str = Form("A"),
):
    """Direct element-wise rate analysis on a provided list of BOQ items.

    items: JSON string array of objects with code, description, quoted_rate, sor_rate, unit, quantity
    """
    try:
        parsed = json.loads(items)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON items: {e}")

    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="items must be a JSON array")

    enriched = []
    for item in parsed:
        enriched.append({
            "item_no": item.get("item_no", ""),
            "code": item.get("code", ""),
            "description": item.get("description", ""),
            "unit": item.get("unit", ""),
            "quantity": item.get("quantity", 0),
            "quoted_rate": item.get("quoted_rate") or item.get("rate"),
            "sor_rate": item.get("sor_rate"),
        })

    analyzed = analyze_boq_items(enriched, zone)

    results = []
    for a in analyzed:
        ra = a.get("rate_analysis", {})
        results.append({
            "sor_code": ra.get("sor_code", a.get("code", "")),
            "description": (ra.get("description", "") or "")[:80],
            "has_composition": ra.get("has_composition", False),
            "total_market_cost_per_unit": ra.get("total_market_cost_per_unit"),
            "profit_margin_vs_market_pct": ra.get("profit_margin_vs_market"),
            "sor_vs_market_pct": ra.get("sor_vs_market_pct"),
            "bid_vs_sor_pct": ra.get("margin_vs_sor"),
            "elements_count": len(ra.get("elements", [])),
            "elements": [
                {
                    "sub_desc": e["sub_desc"],
                    "component": e["component"],
                    "template_qty": e["template_qty"],
                    "template_unit": e["template_unit"],
                    "market_cost": e["market_cost_per_work_unit"],
                    "market_source": e.get("market_source", ""),
                }
                for e in ra.get("elements", [])
            ],
            "coverage_pct": ra.get("coverage_pct", 0),
            "summary": ra.get("summary", ""),
        })

    return JSONResponse({
        "success": True,
        "zone": zone,
        "items_analyzed": len(results),
        "results": results,
    }, ensure_ascii=False)


@router.get("/market-prices", response_model=MarketPricesResponse)
async def market_prices(zone: str = "A"):
    """Get current market prices for construction inputs (materials, labor, equipment)."""
    from app.services.market_index import market_index as market_svc
    rates = market_svc.get_all_rates(zone)
    return {
        "success": True,
        "zone": zone,
        "last_updated": rates.get("last_updated", ""),
        "source": rates.get("source", ""),
        "materials": rates.get("materials", {}),
        "labor": rates.get("labor", {}),
        "equipment": rates.get("equipment", {}),
        "indices": rates.get("indices", {}),
    }


@router.get("/compositions", response_model=CompositionsResponse)
async def list_compositions():
    """List all available rate analysis compositions by SOR code prefix."""
    from app.services.rate_analysis_templates import RATE_ANALYSIS_TEMPLATES
    return {
        "success": True,
        "count": len(RATE_ANALYSIS_TEMPLATES),
        "compositions": [
            {
                "sor_code": code,
                "elements": len(items),
                "materials": sum(1 for i in items if i.get("component") == "material"),
                "labor": sum(1 for i in items if i.get("component") == "labor"),
                "equipment": sum(1 for i in items if i.get("component") == "equipment"),
            }
            for code, items in sorted(RATE_ANALYSIS_TEMPLATES.items())
        ],
    }
