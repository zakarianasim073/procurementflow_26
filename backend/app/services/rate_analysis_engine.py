"""Rate Analysis Engine — element-wise BOQ breakdown with market price comparison & profit margin.

Takes a BOQ item with SOR code, looks up its composition from rate_analysis_templates,
prices each sub-element at both SOR (composite) and MARKET rates, and computes profit margins.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.services.rate_analysis_templates import get_composition
from app.services.market_index import market_index as market_index_svc

logger = logging.getLogger(__name__)

# ── mat_cat → market_index material name mapping ─────────────────────
MATERIAL_MAP = {
    "cement": "Cement (OPC)",
    "sand": "Sand Coarse",
    "aggregate": "Stone Chips",
    "brick": "Brick 1st Class",
    "steel": "MS Rod 60 Grade",
    "bitumen": "Bitumen 80/100",
    "wood": "Timber Garjan",
    "geotextile": None,
    "pipe": "PVC Pipe 4 inch",
}

# ── sub_desc → labor rate mapping (keyword match) ────────────────────
LABOR_KEYWORDS: List[Tuple[str, str]] = [
    # Exact matches first
    ("mason", "Mason 1st Class"),
    ("carpenter", "Carpenter"),
    ("rod bender", "Rod Bender"),
    ("electrician", "Electrician"),
    ("plumber", "Plumber"),
    ("welder", "Welder"),
    # Unskilled before skilled to avoid false match
    ("unskilled", "Unskilled Labor"),
    ("skilled", "Skilled Labor"),
    ("semi", "Semi-Skilled"),
    ("operator", "Semi-Skilled"),
]

# ── sub_desc → equipment rate mapping (keyword match) ────────────────
EQUIP_KEYWORDS: List[Tuple[str, str]] = [
    ("excavator 1", "Excavator 1 cft"),
    ("excavator 0", "Excavator 0.5 cft"),
    ("excavator", "Excavator 1 cft"),
    ("dozer", "Bulldozer D6"),
    ("roller", "Vibratory Roller"),
    ("mixer", "Concrete Mixer"),
    ("dump truck", "Dump Truck"),
    ("truck", "Dump Truck"),
    ("crane", "Crane 15 ton"),
    ("paver", "Paver Finisher"),
    ("pump", "Water Pump 5hp"),
    ("generator", "Generator 50kVA"),
    ("concrete pump", "Concrete Pump"),
    ("boat", "Flat Bed Truck"),
    ("vibrator", "Concrete Mixer"),
    ("mold", "Concrete Mixer"),
    ("rig", "Excavator 1 cft"),
]

# ── Unit conversion factors (template_qty × factor = market unit) ────
# Key: (template_unit, market_unit)
UNIT_CONVERSION = {
    # Labor: market is per DAY, template is per HOUR
    ("hour", "day"): 1.0 / 8.0,
    # Market hours are already per hour
    ("hour", "hour"): 1.0,
    ("hour", "trip"): None,
    # Materials
    ("bag", "bag"): 1.0,
    ("cft", "cft"): 1.0,
    ("pcs", "1000pcs"): 1.0 / 1000.0,
    ("pcs", "pcs"): 1.0,
    ("kg", "ton"): 1.0 / 1000.0,
    ("kg", "kg"): 1.0,
    ("running_meter", "cft"): None,
    ("running_meter", "cft"): None,
    ("liter", "liter"): 1.0,
    ("liter", "litre"): 1.0,
    ("sqm", "sqm"): 1.0,
    ("sqm", "sft"): 10.764,
    ("lump", "hour"): None,
    ("lump", "day"): None,
    ("lump", "lump"): 1.0,
}


def _find_market_rate(sub_item: Dict, zone: str = "A") -> Tuple[Optional[float], str, str]:
    """Find the best market rate for a sub-item. Returns (rate_per_market_unit, market_unit, source_label)."""
    comp = sub_item.get("component", "material")
    desc = sub_item.get("sub_desc", "")
    mat_cat = sub_item.get("mat_cat", "")
    template_unit = sub_item.get("unit", "")
    desc_lower = desc.lower()

    rates = market_index_svc.get_all_rates(zone)

    # Pre-check: Universal keyword matches regardless of component type
    if "scaffolding" in desc_lower or "scaffold" in desc_lower:
        return 250.0, "lump", "Estimate:Scaffolding"
    if "mold" in desc_lower or "vibration" in desc_lower:
        return 500.0, "lump", "Estimate:Mold&Vibration"

    if comp == "material":
        # 1. Direct mat_cat mapping
        if mat_cat and mat_cat in MATERIAL_MAP:
            market_name = MATERIAL_MAP[mat_cat]
            if market_name and market_name in rates.get("materials", {}):
                m = rates["materials"][market_name]
                market_unit = m["unit"]
                adj_rate = m["adjusted_rate"]
                return adj_rate, market_unit, f"Market:{market_name}"

        # 2. Priority: cement, sand, aggregate, brick, steel from desc keywords
        for keyword, market_name in [
            ("cement", "Cement (OPC)"),
            ("sand", "Sand Coarse"),
            ("stone chips", "Stone Chips"),
            ("brick chips", "Stone Chips"),
            ("aggregate", "Stone Chips"),
            ("brick", "Brick 1st Class"),
            ("ms rod", "MS Rod 60 Grade"),
            ("binding wire", "MS Rod 60 Grade"),
            ("nail", "MS Rod 60 Grade"),
            ("plywood", "Timber Garjan"),
            ("timber", "Timber Garjan"),
            ("bitumen", "Bitumen 80/100"),
            ("geotextile", None),
            ("geobag", None),
        ]:
            if keyword in desc_lower and market_name and market_name in rates.get("materials", {}):
                m = rates["materials"][market_name]
                return m["adjusted_rate"], m["unit"], f"Market:{market_name}"

        # 3. Water, fuel — use default values
        if "water" in desc_lower:
            return 0.5, "liter", "Estimate:Water"
        if "fuel" in desc_lower or "diesel" in desc_lower:
            return 85.0, "liter", "Market:Diesel"
        if "earth" in desc_lower or "borrow" in desc_lower:
            return 250.0, "cum", "Estimate:Earth"
        if "mold" in desc_lower:
            return 500.0, "lump", "Estimate:Mold"
        if "cc block" in desc_lower or "precast" in desc_lower:
            return 350.0, "pcs", "Estimate:CC Block"

        return None, "", ""

    elif comp == "labor":
        for keyword, market_name in LABOR_KEYWORDS:
            if keyword in desc_lower and market_name in rates.get("labor", {}):
                m = rates["labor"][market_name]
                return m["adjusted_rate"], m["unit"], f"Market:{market_name}"
        # Fallback
        if "skilled" in desc_lower:
            m = rates.get("labor", {}).get("Skilled Labor", {})
        else:
            m = rates.get("labor", {}).get("Unskilled Labor", {})
        if m:
            return m.get("adjusted_rate", m.get("rate", 0)), m.get("unit", "day"), f"Market:{m.get('name', 'Labor')}"
        return None, "", ""

    elif comp == "equipment":
        for keyword, market_name in EQUIP_KEYWORDS:
            if keyword in desc_lower and market_name in rates.get("equipment", {}):
                m = rates["equipment"][market_name]
                return m["adjusted_rate"], m["unit"], f"Market:{market_name}"
        # Fallback: use description as key
        for equip_name, m in rates.get("equipment", {}).items():
            if any(w in desc_lower for w in equip_name.lower().split()):
                return m["adjusted_rate"], m["unit"], f"Market:{equip_name}"
        return None, "", ""

    return None, "", ""


def _get_unit_conversion_factor(template_unit: str, market_unit: Optional[str]) -> Optional[float]:
    """Get multiplier to convert from template quantity to market unit."""
    if not template_unit or not market_unit:
        return None
    key = (template_unit, market_unit)
    if key in UNIT_CONVERSION:
        return UNIT_CONVERSION[key]
    # Try reverse
    rev_key = (market_unit, template_unit)
    if rev_key in UNIT_CONVERSION and UNIT_CONVERSION[rev_key] is not None:
        return 1.0 / UNIT_CONVERSION[rev_key]
    # Try matching by first part
    for (tu, mu), factor in UNIT_CONVERSION.items():
        if not tu or not mu:
            continue
        if tu in template_unit and mu in market_unit:
            return factor
        if mu in template_unit and tu in market_unit and factor is not None:
            return 1.0 / factor
    return None


def analyze_item(
    sor_code: str,
    description: str,
    quoted_rate: Optional[float],
    sor_rate: Optional[float],
    unit: str = "",
    quantity: float = 0,
    zone: str = "A",
) -> Dict[str, Any]:
    """Analyze a single BOQ item — element breakdown, market prices, profit margin."""
    composition = get_composition(sor_code)
    if not composition:
        return {
            "sor_code": sor_code,
            "description": description,
            "unit": unit,
            "quantity": quantity,
            "quoted_rate": quoted_rate,
            "sor_rate": sor_rate,
            "has_composition": False,
            "elements": [],
            "total_market_cost_per_unit": None,
            "profit_margin_vs_market": None,
            "margin_vs_sor": None,
            "sor_vs_market_pct": None,
            "summary": "No rate analysis template found for this SOR code",
        }

    elements = []
    total_market_cost_per_unit = 0.0
    unmapped_count = 0
    mapped_count = 0

    for sub in composition:
        sub_desc = sub.get("sub_desc", "")
        sub_unit = sub.get("unit", "")
        sub_qty = sub.get("qty", 0)
        sub_comp = sub.get("component", "material")

        # Find market rate
        market_rate_per_unit, market_unit, source = _find_market_rate(sub, zone)
        market_cost = None

        if market_rate_per_unit is not None and sub_qty:
            # Handle unit conversion
            conv = _get_unit_conversion_factor(sub_unit, market_unit)
            if conv is not None:
                adjusted_qty = sub_qty * conv
                market_cost = round(adjusted_qty * market_rate_per_unit, 2)
            else:
                # If units are incompatible but we have a rate, try direct
                market_cost = round(sub_qty * market_rate_per_unit, 2)

        if market_cost is not None:
            total_market_cost_per_unit += market_cost
            mapped_count += 1
        else:
            unmapped_count += 1

        elements.append({
            "sub_desc": sub_desc,
            "component": sub_comp,
            "mat_cat": sub.get("mat_cat", ""),
            "template_unit": sub_unit,
            "template_qty": sub_qty,
            "market_source": source,
            "market_unit": market_unit if market_rate_per_unit else "",
            "market_rate_per_unit": market_rate_per_unit,
            "market_cost_per_work_unit": market_cost,
        })

    # Round total
    total_market_cost_per_unit = round(total_market_cost_per_unit, 2)

    # Profit margins
    profit_margin_vs_market = None
    margin_vs_sor = None
    sor_vs_market_pct = None

    if quoted_rate is not None and quoted_rate > 0 and total_market_cost_per_unit > 0:
        profit_margin_vs_market = round(
            ((quoted_rate - total_market_cost_per_unit) / total_market_cost_per_unit) * 100, 2
        )
    if sor_rate is not None and sor_rate > 0 and total_market_cost_per_unit > 0:
        sor_vs_market_pct = round(
            ((sor_rate - total_market_cost_per_unit) / total_market_cost_per_unit) * 100, 2
        )
    if quoted_rate is not None and sor_rate is not None and sor_rate > 0:
        margin_vs_sor = round(
            ((quoted_rate - sor_rate) / sor_rate) * 100, 2
        )

    coverage_pct = round((mapped_count / max(len(composition), 1)) * 100, 1)

    # Build ratio breakdown
    pct_of_cost = []
    for el in elements:
        mc = el.get("market_cost_per_work_unit")
        if mc is not None and total_market_cost_per_unit > 0:
            pct_of_cost.append(round((mc / total_market_cost_per_unit) * 100, 1))
        else:
            pct_of_cost.append(None)

    return {
        "sor_code": sor_code,
        "description": description,
        "unit": unit,
        "quantity": quantity,
        "quoted_rate": quoted_rate,
        "sor_rate": sor_rate,
        "has_composition": True,
        "elements": elements,
        "pct_of_cost": pct_of_cost,
        "total_market_cost_per_unit": total_market_cost_per_unit,
        "total_market_cost_total": round(total_market_cost_per_unit * quantity, 2) if quantity else None,
        "mapped_elements": mapped_count,
        "unmapped_elements": unmapped_count,
        "coverage_pct": coverage_pct,
        "profit_margin_vs_market": profit_margin_vs_market,
        "margin_vs_sor": margin_vs_sor,
        "sor_vs_market_pct": sor_vs_market_pct,
        "summary": _build_summary(
            quoted_rate, sor_rate, total_market_cost_per_unit,
            profit_margin_vs_market, margin_vs_sor, sor_vs_market_pct,
        ),
    }


def _build_summary(quoted, sor, market_cost, margin_market, margin_sor, sor_vs_market):
    parts = []
    if quoted is not None and market_cost and market_cost > 0:
        parts.append(f"Market cost: BDT {market_cost}/unit")
        parts.append(f"Profit margin vs market: {margin_market:+.1f}%")
    if sor is not None and market_cost and market_cost > 0:
        sor_diff = sor - market_cost
        parts.append(f"SOR vs market: {sor_vs_market:+.1f}% (BDT {sor_diff:+.0f}/unit)")
    if quoted is not None and sor is not None and sor > 0:
        parts.append(f"Bid vs SOR: {margin_sor:+.1f}%")
    return " | ".join(parts) if parts else "Insufficient data for cost analysis"


def analyze_boq_items(
    items: List[Dict[str, Any]],
    zone: str = "A",
) -> List[Dict[str, Any]]:
    """Analyze a list of BOQ comparison items — returns enriched results with element breakdowns."""
    results = []
    for item in items:
        sor_code = item.get("code", "") or item.get("sor_source", "")
        desc = item.get("desc", "") or item.get("description", "")
        quoted = item.get("rate") or item.get("quoted_rate")
        sor = item.get("sor_rate")
        unit = item.get("unit", "")
        qty = item.get("qty", 0) or item.get("quantity", 0)

        if sor_code and sor_code != "0":
            analysis = analyze_item(sor_code, desc, quoted, sor, unit, qty, zone)
        else:
            analysis = {
                "sor_code": sor_code or "(no code)",
                "description": desc,
                "has_composition": False,
                "summary": "No SOR code — cannot perform rate analysis",
            }

        results.append({
            **item,
            "rate_analysis": analysis,
        })
    return results
