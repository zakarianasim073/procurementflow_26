"""Regenerate golden files for the SOR/BOQ behavioral contract (T-007 / TST-01a).

Run from backend/:  python tests/golden/generate_golden.py

DO NOT regenerate casually — the golden files ARE the contract (ADR-003).
Regeneration is only legitimate when a ticket explicitly changes SOR/BOQ
behavior; the diff of the golden JSON is then part of that ticket's review.
"""
from __future__ import annotations

import asyncio
import csv
import json
import sys
from pathlib import Path

GOLDEN_DIR = Path(__file__).resolve().parent
BACKEND = GOLDEN_DIR.parents[1]
sys.path.insert(0, str(BACKEND))

from app.sor.sor_service import SORService  # noqa: E402

# ── SOR corpus ──────────────────────────────────────────────────────────
# Edge cases per ADR-003: exact codes (all agencies), group-prefix matches,
# (AGENCY) suffix detection, compound A&B codes, unknown codes, fuzzy-only
# descriptions, all four zones incl. the LGED vs PWD/BWDB C↔D swap.

HANDCRAFTED = [
    # (code, description, agency_hint, zone)
    ("04-180-00", "", "BWDB", "A"),                      # BWDB exact
    ("04-180-00", "", "BWDB", "B"),
    ("04-180-00", "", "BWDB", "C"),
    ("04-180-00", "", "BWDB", "D"),
    ("08-100", "", "BWDB", "A"),                          # group prefix → sub-item
    ("04-815-00(BWDB)", "", "PWD", "B"),                  # suffix overrides hint
    ("01.1.1", "", "PWD", "A"),                           # PWD exact dotted
    ("01.1.1(PWD)", "", "BWDB", "C"),                     # PWD suffix + zone C (Khulna for PWD)
    ("01.1.4.1", "", "PWD", "D"),                         # deep dotted, PWD zone D (Rajshahi)
    ("1.01.01", "", "LGED", "A"),                         # LGED exact
    ("1.01.01(LGED)", "", "BWDB", "D"),                   # LGED suffix + LGED zone D (Khulna)
    ("1.02", "", "LGED", "C"),                            # LGED zone C (Rajshahi)
    ("XX&01.1.2", "", "PWD", "A"),                        # compound A&B → B part
    ("ZZZ-999-99", "", "BWDB", "A"),                      # unknown → None
    ("", "Engineer's site office of minimum 10 sqm plinth area with office furniture", "PWD", "A"),  # fuzzy only
    ("NOCODE", "Project Profile Signboard providing and fixing typical project profile signboard retro-reflective", "LGED", "B"),  # bad code → fuzzy
]

FUZZY_CASES = [
    ("Engineer's site office of minimum 15 sqm plinth area with water purifier", "PWD", "A", "job"),
    ("land removing debris including", "BWDB", "B", "sqm"),
    ("completely unrelated gibberish text zzz qqq", "PWD", "A", ""),  # below threshold → None
]


def _sample_csv_codes(agency: str, n: int = 5) -> list[str]:
    codes = []
    with open(BACKEND / "app" / "sor" / agency.lower() / "rates.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = (row.get("code") or "").strip()
            if code and len(code) > 3:
                codes.append(code)
            if len(codes) >= n:
                break
    return codes


def generate_sor() -> None:
    svc = SORService()
    svc.load_all(prefer_db=False)  # CSV = committed source of truth, hermetic

    cases = list(HANDCRAFTED)
    for agency in ("BWDB", "PWD", "LGED"):
        for code in _sample_csv_codes(agency):
            cases.append((code, "", agency, "A"))
            cases.append((code, "", agency, "D"))

    golden = []
    for code, desc, agency, zone in cases:
        rate, record = svc.find_rate(code, desc, agency=agency, zone=zone)
        golden.append({
            "code": code, "description": desc, "agency": agency, "zone": zone,
            "expect": None if record is None else {
                "rate": rate,
                "matched_code": record.code,
                "matched_agency": record.agency,
                "unit": record.unit,
            },
        })

    fuzzy = []
    for desc, agency, zone, unit in FUZZY_CASES:
        rate, record, score = svc.find_rate_by_description(desc, agency, zone, unit=unit)
        fuzzy.append({
            "description": desc, "agency": agency, "zone": zone, "unit": unit,
            "expect": None if record is None else {
                "rate": rate, "matched_code": record.code, "score": score,
            },
            "score": score,
        })

    out = {"find_rate": golden, "find_rate_by_description": fuzzy}
    (GOLDEN_DIR / "sor_golden.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"sor_golden.json: {len(golden)} find_rate + {len(fuzzy)} fuzzy cases")


def generate_boq() -> None:
    from app.services.pdf_parser import PDFParser

    pdf = GOLDEN_DIR / "fixtures" / "boq_1290886.pdf"
    items = asyncio.run(PDFParser().extract_boq_items(str(pdf)))
    golden = {
        "source": pdf.name,
        "item_count": len(items),
        "codes": [i.get("code", "") for i in items],
        "items": [
            {
                "code": i.get("code", ""),
                "unit": i.get("unit", ""),
                "quantity": i.get("quantity"),
                "description_prefix": (i.get("description") or "")[:80],
            }
            for i in items
        ],
    }
    (GOLDEN_DIR / "boq_golden.json").write_text(json.dumps(golden, indent=1), encoding="utf-8")
    print(f"boq_golden.json: {len(items)} items from {pdf.name}")


if __name__ == "__main__":
    generate_sor()
    generate_boq()
