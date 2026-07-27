"""Golden SOR matching tests (T-007 / ADR-003) — the behavioral contract.

If one of these fails, the SOR match ladder changed. That is only legitimate
inside a ticket that explicitly versions the behavior; regenerate via
tests/golden/generate_golden.py and review the JSON diff in that ticket.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.sor.sor_service import SORService

GOLDEN = json.loads((Path(__file__).parent / "golden" / "sor_golden.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sor():
    svc = SORService()
    svc.load_all(prefer_db=False)  # committed CSVs — hermetic, no DB needed
    return svc


@pytest.mark.parametrize(
    "case", GOLDEN["find_rate"],
    ids=[f"{c['agency']}-{c['zone']}-{c['code'] or c['description'][:20]}" for c in GOLDEN["find_rate"]],
)
def test_find_rate_golden(sor, case):
    rate, record = sor.find_rate(
        case["code"], case["description"], agency=case["agency"], zone=case["zone"]
    )
    if case["expect"] is None:
        assert record is None, f"expected no match, got {record.code}"
    else:
        assert record is not None, "expected a match, got None"
        assert record.code == case["expect"]["matched_code"]
        assert record.agency == case["expect"]["matched_agency"]
        assert rate == pytest.approx(case["expect"]["rate"])
        assert record.unit == case["expect"]["unit"]


@pytest.mark.parametrize(
    "case", GOLDEN["find_rate_by_description"],
    ids=[c["description"][:30] for c in GOLDEN["find_rate_by_description"]],
)
def test_find_rate_by_description_golden(sor, case):
    rate, record, score = sor.find_rate_by_description(
        case["description"], case["agency"], case["zone"], unit=case["unit"]
    )
    assert score == pytest.approx(case["score"], abs=1e-3)
    if case["expect"] is None:
        assert record is None
    else:
        assert record is not None
        assert record.code == case["expect"]["matched_code"]
        assert rate == pytest.approx(case["expect"]["rate"])


def test_fuzzy_threshold_is_042(sor):
    """ADR-003: the fuzzy threshold is frozen at 0.42."""
    import inspect
    sig = inspect.signature(sor.find_rate_by_description)
    assert sig.parameters["threshold"].default == 0.42
