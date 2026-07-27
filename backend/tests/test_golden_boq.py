"""Golden BOQ parse tests (T-007 / ADR-003) — freezes PDF parser output.

Fixture: tests/golden/fixtures/boq_1290886.pdf (real e-GP BWDB bundle BOQ).
Regenerate via tests/golden/generate_golden.py only inside a ticket that
deliberately changes parser behavior.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.pdf_parser import PDFParser

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN = json.loads((GOLDEN_DIR / "boq_golden.json").read_text(encoding="utf-8"))
FIXTURE = GOLDEN_DIR / "fixtures" / "boq_1290886.pdf"


@pytest.fixture(scope="module")
def parsed():
    import asyncio
    return asyncio.new_event_loop().run_until_complete(
        PDFParser().extract_boq_items(str(FIXTURE))
    )


def test_item_count_frozen(parsed):
    assert len(parsed) == GOLDEN["item_count"]


def test_all_codes_frozen(parsed):
    assert [i.get("code", "") for i in parsed] == GOLDEN["codes"]


def test_items_frozen(parsed):
    for item, expect in zip(parsed, GOLDEN["items"]):
        assert item.get("code", "") == expect["code"]
        assert item.get("unit", "") == expect["unit"]
        assert item.get("quantity") == pytest.approx(expect["quantity"]) if expect["quantity"] is not None else item.get("quantity") is None
        assert (item.get("description") or "")[:80] == expect["description_prefix"]


def test_every_item_has_code_and_unit(parsed):
    """Structural invariant of the BWDB table parser."""
    for item in parsed:
        assert item.get("code"), f"item without code: {item}"
        assert item.get("unit"), f"item without unit: {item}"
