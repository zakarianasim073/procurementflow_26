"""W-008 — BOQ arithmetic checks: catches 100% of seeded errors, zero false positives.

Builds a synthetic priced BOQ xlsx (openpyxl), seeds known qty x rate != amount
errors, runs the parser + checker, and asserts exact detection.
"""

from __future__ import annotations

import pytest
import openpyxl

from app.services.boq_processor import BOQProcessor
from app.services.excel_parser import ExcelParser

# (item_no, code, description, unit, qty, rate, stated_amount, is_error)
ROWS = [
    ("1", "04-180-00", "Earthwork in excavation", "cum", 120.0, 250.50, 30060.00, False),
    ("2", "07-110-10", "Brick work in cement mortar", "cum", 45.5, 8200.00, 373100.00, False),
    ("3", "12-330-00", "RCC works in slab", "cum", 10.0, 12500.00, 130000.00, True),   # should be 125000
    ("4", "05-210-00", "Sand filling", "cum", 300.0, 95.00, 28500.00, False),
    ("5", "18-450-00", "Painting two coats", "sqm", 80.0, 145.00, 11700.00, True),     # should be 11600
    ("6", "09-120-00", "CC works (1:2:4)", "cum", 25.0, 9800.00, 245000.00, False),
    ("7", "03-140-00", "Site clearance", "sqm", 500.0, 12.00, 6001.00, False),          # within 1 Tk tolerance
    ("8", "11-220-00", "Steel reinforcement", "kg", 1500.0, 92.00, 148000.00, True),   # should be 138000
]

SEEDED_ERROR_ITEMS = {r[0] for r in ROWS if r[7]}


@pytest.fixture()
def boq_xlsx(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Item No", "Code", "Description", "Unit", "Qty", "Rate (Tk)", "Amount (Tk)"])
    for item_no, code, desc, unit, qty, rate, amount, _ in ROWS:
        ws.append([item_no, code, desc, unit, qty, rate, amount])
    path = tmp_path / "seeded_boq.xlsx"
    wb.save(path)
    return str(path)


@pytest.mark.asyncio
async def test_parser_captures_amount_column(boq_xlsx):
    items = await ExcelParser().extract_boq_items(boq_xlsx)
    assert len(items) == len(ROWS)
    assert all(item["amount"] is not None for item in items)


@pytest.mark.asyncio
async def test_catches_all_seeded_errors_and_only_those(boq_xlsx):
    items = await ExcelParser().extract_boq_items(boq_xlsx)
    errors = BOQProcessor.check_arithmetic(items)

    caught = {e["item_no"] for e in errors}
    assert caught == SEEDED_ERROR_ITEMS, (
        f"missed: {SEEDED_ERROR_ITEMS - caught}; false positives: {caught - SEEDED_ERROR_ITEMS}"
    )
    for e in errors:
        assert e["flag"] == "ARITHMETIC ERROR"
        assert e["computed_amount"] != e["stated_amount"]
        assert e["difference"] == round(e["stated_amount"] - e["computed_amount"], 2)


def test_items_missing_values_are_skipped_not_guessed():
    items = [
        {"item_no": "1", "quantity": 10, "rate": None, "amount": 100},
        {"item_no": "2", "quantity": None, "rate": 10, "amount": 100},
        {"item_no": "3", "quantity": 10, "rate": 10},  # unpriced tender BOQ line
    ]
    assert BOQProcessor.check_arithmetic(items) == []


def test_rounding_within_tolerance_not_flagged():
    items = [{"item_no": "1", "quantity": 3.0, "rate": 33.333, "amount": 100.00}]
    assert BOQProcessor.check_arithmetic(items) == []
