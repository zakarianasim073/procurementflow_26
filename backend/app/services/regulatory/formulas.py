"""One Python function per Rule.formula_kind — parameterized, not eval/exec.

Every function has the signature:
    (inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]
returning at least {"decision", "passed", "outputs", "intermediate_values"}.

RuleEngine.evaluate() looks up the function via FORMULA_REGISTRY[formula_kind]
and never executes stored strings as code.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List


def _get(inputs: Dict[str, Any], field: str, default: Any = 0) -> Any:
    return inputs.get(field, default)


# ── RATIO_THRESHOLD_BAND ─────────────────────────────────────────────────
# Used by: SLT/ALT detection (ITT 52.2), PPR2008 symmetric cap (via cap_pct).

def ratio_threshold_band(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    numerator = float(_get(inputs, parameters.get("numerator_field", "quoted_amount")))
    denominator = float(_get(inputs, parameters.get("denominator_field", "estimated_value")))
    ratio = numerator / denominator if denominator else 0.0

    if "cap_pct" in parameters:
        # Symmetric cap around a center (PPR2008 style): normal if ratio is
        # within [center - cap_pct, center + cap_pct], else out-of-band.
        center = float(parameters.get("center", 1.0))
        cap_pct = float(parameters["cap_pct"])
        lower, upper = center - cap_pct, center + cap_pct
        within = lower <= ratio <= upper
        decision = "Normal" if within else ("BelowCap" if ratio < lower else "AboveCap")
        return {
            "decision": decision,
            "passed": within,
            "outputs": {"ratio": ratio, "lower_bound": lower, "upper_bound": upper},
            "intermediate_values": {"numerator": numerator, "denominator": denominator},
        }

    bands: List[Dict[str, Any]] = parameters.get("bands", [])
    decision = bands[-1]["label"] if bands else "Normal"
    for band in bands:
        max_ratio = band.get("max_ratio")
        if max_ratio is not None and ratio < max_ratio:
            decision = band["label"]
            break
    passed = bool(bands) and decision == bands[-1]["label"]
    return {
        "decision": decision,
        "passed": passed,
        "outputs": {"ratio": ratio, "discount_pct": round((1 - ratio) * 100, 2)},
        "intermediate_values": {"numerator": numerator, "denominator": denominator},
    }


# ── PERCENTAGE_OF ────────────────────────────────────────────────────────
# Used by: bid security (ITT 19.1), performance security (GCC 66.1),
# advance payment (GCC 72.1), retention (GCC 68.1/68.2), subcontract limit
# (ITT 7.1).

def percentage_of(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    base = float(_get(inputs, parameters.get("base_field", "estimated_value")))
    pct = float(parameters.get("pct", 0.0))
    mode = parameters.get("mode", "cap")
    max_absolute = parameters.get("max_absolute")

    required = base * pct
    if max_absolute is not None:
        required = min(required, float(max_absolute))

    outputs: Dict[str, Any] = {"required_amount": round(required, 2), "base_amount": base, "pct": pct}
    intermediate: Dict[str, Any] = {}

    if mode == "min_of":
        # e.g. advance payment: recommended = min(mobilization_required, max_advance)
        mobilization_required = float(_get(inputs, "mobilization_required", required))
        recommended = min(mobilization_required, required)
        outputs["max_advance"] = round(required, 2)
        outputs["recommended_advance"] = round(recommended, 2)
        return {
            "decision": "COMPUTED",
            "passed": True,
            "outputs": outputs,
            "intermediate_values": intermediate,
        }

    if mode == "retention":
        # e.g. GCC 68.1/68.2: per-invoice retention capped cumulatively.
        cap_pct = float(parameters.get("cap_pct", pct * 2))
        monthly_invoices: List[float] = [float(x) for x in _get(inputs, "monthly_invoices", [])]
        total_invoiced = sum(monthly_invoices)
        retention_deducted = min(total_invoiced * pct, total_invoiced * cap_pct)
        outputs["total_invoiced"] = round(total_invoiced, 2)
        outputs["retention_deducted"] = round(retention_deducted, 2)
        outputs["retention_cap"] = round(total_invoiced * cap_pct, 2)
        return {
            "decision": "COMPUTED",
            "passed": True,
            "outputs": outputs,
            "intermediate_values": intermediate,
        }

    # default "cap" mode: compare an actual/submitted amount against the required amount.
    actual_field = parameters.get("actual_field", "submitted_amount")
    if actual_field in inputs:
        actual = float(inputs[actual_field])
        adequate = actual >= required
        outputs["actual_amount"] = actual
        outputs["adequate"] = adequate
        return {
            "decision": "ADEQUATE" if adequate else "INADEQUATE",
            "passed": adequate,
            "outputs": outputs,
            "intermediate_values": intermediate,
        }

    return {
        "decision": "COMPUTED",
        "passed": True,
        "outputs": outputs,
        "intermediate_values": intermediate,
    }


# ── ARITHMETIC_ERROR_TOLERANCE ───────────────────────────────────────────
# Used by: ITT 27. Canonical statistic = AMOUNT_WEIGHTED (resolves the
# ppr_engine.py vs ppr_evaluation.py contradiction found in the codebase
# audit — item-count-ratio is retired, not offered as an alternative here).

def arithmetic_error_tolerance(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    boq_items: List[Dict[str, Any]] = _get(inputs, "boq_items", [])
    max_error_pct = float(parameters.get("max_error_pct", 0.20))

    corrections = []
    total_original = 0.0
    total_correction = 0.0
    for item in boq_items:
        qty = float(item.get("qty", item.get("quantity", 0)) or 0)
        rate = float(item.get("rate", 0) or 0)
        amount = float(item.get("amount", qty * rate) or 0)
        calculated = qty * rate
        total_original += amount
        variance = abs(calculated - amount)
        if variance > 1.0:
            total_correction += variance
            corrections.append({
                "item_no": item.get("item_no"),
                "stated_amount": amount,
                "calculated_amount": calculated,
                "variance": variance,
            })

    correction_pct = (total_correction / total_original * 100) if total_original > 0 else 0.0
    is_rejectable = correction_pct > (max_error_pct * 100)

    return {
        "decision": "REJECTABLE" if is_rejectable else "ACCEPTABLE",
        "passed": not is_rejectable,
        "outputs": {
            "correction_pct": round(correction_pct, 2),
            "max_error_pct": max_error_pct * 100,
            "total_original": round(total_original, 2),
            "total_correction": round(total_correction, 2),
            "corrected_items_count": len(corrections),
        },
        "intermediate_values": {"corrections": corrections},
    }


# ── WEIGHTED_AVERAGE_ADVISORY ────────────────────────────────────────────
# Advisory bid-strategy heuristic (NOT a compliance verdict — Rule.is_legal_
# mandate=False for this rule). Canonical weights: 0.2(OCE)/0.5(bidder-avg)
# /0.3(NPPI) + std-dev subtraction (slt_analysis.py's variant, chosen over
# decision_calibration.py's 0.5/0.3/0.2-no-stddev variant per audit).

def weighted_average_advisory(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    weights = parameters.get("weights", {"oce": 0.2, "bidder_avg": 0.5, "nppi_adjusted": 0.3})
    subtract_stddev = bool(parameters.get("subtract_stddev", True))

    oce = float(_get(inputs, "oce", 0))
    nppi = float(_get(inputs, "nppi", 0))
    bidder_prices: List[float] = [float(x) for x in _get(inputs, "bidder_prices", [])]

    x_nppi = oce * nppi
    if bidder_prices:
        avg_bidder_price = sum(bidder_prices) / len(bidder_prices)
    else:
        avg_bidder_price = float(_get(inputs, "avg_bidder_price", oce * 0.97))

    weighted_average = (
        weights.get("oce", 0.2) * oce
        + weights.get("bidder_avg", 0.5) * avg_bidder_price
        + weights.get("nppi_adjusted", 0.3) * x_nppi
    )

    if len(bidder_prices) >= 2:
        mean = sum(bidder_prices) / len(bidder_prices)
        variance = sum((mean - x) ** 2 for x in bidder_prices) / len(bidder_prices)
        stddev = math.sqrt(variance)
    else:
        stddev = oce * 0.02  # fallback estimate, ~2% of OCE, matching slt_analysis.py

    advisory_threshold = weighted_average - stddev if subtract_stddev else weighted_average

    return {
        "decision": "ADVISORY",
        "passed": True,  # informational — not a compliance gate
        "outputs": {
            "weighted_average": round(weighted_average, 2),
            "stddev": round(stddev, 2),
            "advisory_threshold": round(advisory_threshold, 2),
        },
        "intermediate_values": {"x_nppi": x_nppi, "avg_bidder_price": avg_bidder_price},
    }


# ── SCORE_WEIGHTED_CRITERIA ───────────────────────────────────────────────
# Used by: TEC Schedule 4/5/6 scoring.

def score_weighted_criteria(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    criteria: Dict[str, Dict[str, float]] = parameters.get("criteria", {})
    pass_pct = float(parameters.get("pass_pct", 0.70))
    scores: Dict[str, float] = _get(inputs, "scores", {})

    weighted_sum = 0.0
    total_weight = 0.0
    per_criterion = {}
    for name, spec in criteria.items():
        max_score = float(spec.get("max", 1))
        weight = float(spec.get("weight", 0))
        raw = float(scores.get(name, 0))
        pct = max(0.0, min(1.0, raw / max_score)) if max_score else 0.0
        weighted_sum += pct * weight
        total_weight += weight
        per_criterion[name] = {"raw": raw, "max": max_score, "pct": round(pct * 100, 2), "weight": weight}

    overall_pct = (weighted_sum / total_weight) if total_weight else 0.0
    passed = overall_pct >= pass_pct

    return {
        "decision": "PASS" if passed else "FAIL",
        "passed": passed,
        "outputs": {"overall_pct": round(overall_pct * 100, 2), "pass_pct": pass_pct * 100},
        "intermediate_values": {"per_criterion": per_criterion},
    }


# ── TENDER_CAPACITY ───────────────────────────────────────────────────────
# Used by: ITT 14.1(d).

def tender_capacity(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    turnover_multiplier = float(parameters.get("turnover_multiplier", 2.0))
    min_turnover_ratio = float(parameters.get("min_turnover_ratio", 0.5))
    experience_bands: List[Dict[str, Any]] = parameters.get(
        "experience_years_by_value", [{"threshold": 0, "years": 3}]
    )

    annual_turnover = float(_get(inputs, "annual_turnover", 0))
    current_commitments = float(_get(inputs, "current_commitments", 0))
    tender_estimated_value = float(_get(inputs, "tender_estimated_value", 0))
    years_in_business = float(_get(inputs, "years_in_business", 0))

    available_capacity = max(annual_turnover * turnover_multiplier - current_commitments, 0.0)
    turnover_ratio = (annual_turnover / tender_estimated_value) if tender_estimated_value > 0 else 0.0
    eligible = available_capacity >= tender_estimated_value and turnover_ratio >= min_turnover_ratio

    min_experience_years = 3
    for band in sorted(experience_bands, key=lambda b: -b.get("threshold", 0)):
        if tender_estimated_value > band.get("threshold", 0):
            min_experience_years = band.get("years", 3)
            break
    experience_met = years_in_business >= min_experience_years

    if eligible:
        status, score = "ELIGIBLE", 100
    elif available_capacity >= tender_estimated_value * 0.7:
        status, score = "MARGINAL", 60
    else:
        status, score = "INADEQUATE", 20

    return {
        "decision": status,
        "passed": eligible,
        "outputs": {
            "available_capacity": round(available_capacity, 2),
            "turnover_ratio": round(turnover_ratio, 2),
            "score": score,
            "min_experience_years": min_experience_years,
            "experience_met": experience_met,
        },
        "intermediate_values": {},
    }


# ── MIN_COUNT / MAX_COUNT ────────────────────────────────────────────────
# Used by: eligibility min-engineers floor, JV max-partners ceiling.

def min_count(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    field = parameters.get("field", "count")
    minimum = float(parameters.get("min", 0))
    actual = float(_get(inputs, field, 0))
    passed = actual >= minimum
    return {
        "decision": "PASS" if passed else "FAIL",
        "passed": passed,
        "outputs": {"actual": actual, "min_required": minimum},
        "intermediate_values": {},
    }


def max_count(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    field = parameters.get("field", "count")
    maximum = float(parameters.get("max", 0))
    actual = float(_get(inputs, field, 0))
    passed = actual <= maximum
    return {
        "decision": "PASS" if passed else "FAIL",
        "passed": passed,
        "outputs": {"actual": actual, "max_allowed": maximum},
        "intermediate_values": {},
    }


# ── REFERENCE ────────────────────────────────────────────────────────────
# Used by: policy/process rules that cannot be numerically evaluated in this
# pass (e.g. "TEC must include ≥1 member from another PE"). They are stored
# for traceability and display; evaluation returns the parameters as info and
# does not gate a tender.

def reference(inputs: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "decision": "REFERENCE",
        "passed": None,
        "outputs": {
            "note": parameters.get("note", "Non-numeric policy rule; manual/display only."),
            "parameters": parameters,
        },
        "intermediate_values": {},
    }


FORMULA_REGISTRY: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {
    "RATIO_THRESHOLD_BAND": ratio_threshold_band,
    "PERCENTAGE_OF": percentage_of,
    "ARITHMETIC_ERROR_TOLERANCE": arithmetic_error_tolerance,
    "WEIGHTED_AVERAGE_ADVISORY": weighted_average_advisory,
    "SCORE_WEIGHTED_CRITERIA": score_weighted_criteria,
    "TENDER_CAPACITY": tender_capacity,
    "MIN_COUNT": min_count,
    "MAX_COUNT": max_count,
    "REFERENCE": reference,
}
