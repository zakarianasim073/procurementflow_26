"""W-006 — Qualification Checker rule engine (EligibilityComplianceAgent v2.1.0).

Deterministic seeded cases per criterion, plus the Validation Dataset harness
(50 real TDS docs) which skips until the dataset lands at
backend/tests/data/validation_dataset/qualification/.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.core.base import AgentStatus
from app.agents.evaluation.eligibility_compliance import EligibilityComplianceAgent

DATASET = Path(__file__).parent / "data" / "validation_dataset" / "qualification"

QUALIFIED_PROFILE = {
    "company_name": "Test Constructions Ltd",
    "years_experience": 10,
    "avg_turnover": 60_000_000,
    "equipment": ["excavator", "mixer", "roller"],
    "engineers_count": 6,
    "licenses": ["trade"],
    "similar_works": [
        {"title": "Embankment A", "value_bdt": 30_000_000},
        {"title": "Regulator B", "value_bdt": 45_000_000},
    ],
}

REQUIREMENTS = {
    "experience_required": "5 years",
    "turnover_required": 50_000_000,
    "similar_works_required": 2,
    "min_similar_work_value_bdt": 25_000_000,
}

SPECS = {"required_equipment": ["excavator", "mixer"]}


def _context(profile: dict, requirements: dict = REQUIREMENTS, specs: dict = SPECS) -> dict:
    return {
        "company_profile": profile,
        "upstream": {
            "agent-004-document-ai": requirements,
            "agent-006-spec-intelligence": specs,
        },
    }


async def _run(profile: dict, requirements: dict = REQUIREMENTS, specs: dict = SPECS):
    result = await EligibilityComplianceAgent().execute(_context(profile, requirements, specs))
    assert result.status == AgentStatus.SUCCESS
    return result.output


@pytest.mark.asyncio
async def test_fully_qualified_profile_is_compliant():
    output = await _run(QUALIFIED_PROFILE)
    assert output["compliant"] is True
    assert all(output["checks"].values())
    assert output["missing_items"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override,failed_check",
    [
        ({"years_experience": 3}, "experience_met"),
        ({"avg_turnover": 10_000_000}, "turnover_met"),
        ({"equipment": ["mixer"]}, "equipment_met"),
        ({"engineers_count": 2}, "personnel_met"),
        ({"licenses": []}, "licenses_met"),
        ({"similar_works": [{"title": "small", "value_bdt": 1_000_000}]}, "similar_works_met"),
    ],
)
async def test_each_criterion_fails_independently(override, failed_check):
    profile = {**QUALIFIED_PROFILE, **override}
    output = await _run(profile)
    assert output["compliant"] is False
    assert output["checks"][failed_check] is False
    assert output["missing_items"], "gaps must be reported"


@pytest.mark.asyncio
async def test_similar_works_value_threshold_filters_small_works():
    profile = {
        **QUALIFIED_PROFILE,
        "similar_works": [
            {"title": "big", "value_bdt": 30_000_000},
            {"title": "too-small", "value_bdt": 24_999_999},
        ],
    }
    output = await _run(profile)
    assert output["checks"]["similar_works_met"] is False
    assert any("similar works" in item for item in output["missing_items"])


@pytest.mark.asyncio
async def test_similar_works_waived_when_tds_omits_requirement():
    requirements = {k: v for k, v in REQUIREMENTS.items() if not k.startswith(("similar", "min_similar"))}
    profile = {**QUALIFIED_PROFILE, "similar_works": []}
    output = await _run(profile, requirements=requirements)
    assert output["checks"]["similar_works_met"] is True


def _label(value) -> bool:
    """Accept bool or PASS/FAIL strings from labelers."""
    if isinstance(value, bool):
        return value
    return str(value).strip().upper() in ("PASS", "TRUE", "YES", "QUALIFIED")


@pytest.mark.asyncio
async def test_validation_dataset_agreement():
    """W-006 acceptance: >=95% agreement with manual checks on 50 real TDS docs.

    Prints precision/recall/FP/FN + disagreement cases for regression analysis.
    """
    cases = sorted(DATASET.glob("*.json")) if DATASET.exists() else []
    cases = [c for c in cases if json.loads(c.read_text(encoding="utf-8")).get("manual_decision") is not None]
    if len(cases) < 50:
        pytest.skip(f"Validation Dataset incomplete ({len(cases)}/50 labeled cases present)")

    tp = fp = tn = fn = 0
    disagreements = []
    for case_file in cases:
        case = json.loads(case_file.read_text(encoding="utf-8"))
        output = await _run(case["profile"], case["requirements"], case.get("specs", {}))
        predicted, manual = output["compliant"], _label(case["manual_decision"])
        if predicted and manual:
            tp += 1
        elif predicted and not manual:
            fp += 1
        elif not predicted and not manual:
            tn += 1
        else:
            fn += 1
        if predicted != manual:
            disagreements.append(f"{case_file.name}: engine={predicted} manual={manual} ({case.get('manual_reason', '')})")

    agree = (tp + tn) / len(cases)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    print(f"\nW-006 agreement={agree:.1%} precision={precision:.1%} recall={recall:.1%} "
          f"TP={tp} FP={fp} TN={tn} FN={fn}")
    for d in disagreements:
        print("  DISAGREE", d)
    assert agree >= 0.95
