"""
app_diagnostic.py
Standalone diagnostic for the APP (Annual Procurement Plan) crawler.

The APP crawler produced zero output rows. Rather than guessing at why,
this script hits the known APP search entry point, saves the raw HTML,
and logs every candidate selector/link-text/label it can find so the
real current markup can be compared against what the crawler expects
(exact-text matches like "DB"/"RB"/"OF" for budget type, or a specific
href pattern for package detail links).

Run this manually, then inspect:
  - app_diagnostic_raw.html   (full page source, for manual review)
  - app_diagnostic_report.json (structured findings)
"""

import json
import logging
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("app_diagnostic")

BASE_URL = "https://www.eprocure.gov.bd"
APP_SEARCH_URL = f"{BASE_URL}/DeptTree.jsp"
APP_SEARCH_PARAMS = {"operation": "AdvAPPSearch"}

MAINTENANCE_MARKERS = [
    "will remain temporarily unavailable",
    "scheduled maintenance activities of the e-GP System",
]

RAW_HTML_PATH = Path("app_diagnostic_raw.html")
REPORT_PATH = Path("app_diagnostic_report.json")


def is_maintenance_banner(html_text: str) -> bool:
    if not html_text:
        return False
    lowered = html_text.lower()
    return any(marker.lower() in lowered for marker in MAINTENANCE_MARKERS)


def fetch_raw(url: str, params=None) -> str:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; ProcureBot/1.0)"})
    resp = session.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.text


def diagnose():
    report = {
        "url_requested": APP_SEARCH_URL,
        "params": APP_SEARCH_PARAMS,
        "hit_maintenance_banner": False,
        "http_status_ok": False,
        "all_link_texts": [],
        "all_link_hrefs_sample": [],
        "budget_type_candidates": [],
        "table_count": 0,
        "table_row_counts": [],
        "form_field_names": [],
        "notes": [],
    }

    try:
        html_text = fetch_raw(APP_SEARCH_URL, params=APP_SEARCH_PARAMS)
        report["http_status_ok"] = True
    except requests.RequestException as exc:
        report["notes"].append(f"Request failed entirely: {exc}")
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        log.error("APP search page could not be fetched at all: %s", exc)
        return

    RAW_HTML_PATH.write_text(html_text, encoding="utf-8")

    if is_maintenance_banner(html_text):
        report["hit_maintenance_banner"] = True
        report["notes"].append(
            "APP search page returned the e-GP maintenance marquee instead "
            "of real content -- crawler likely ran during a maintenance "
            "window and returned zero rows because there WAS no listing to "
            "parse, not because selectors broke."
        )
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        log.warning("Maintenance banner detected -- see notes in report")
        return

    soup = BeautifulSoup(html_text, "html.parser")

    # Every visible link's text -- to compare against expected "DB"/"RB"/"OF"
    links = soup.find_all("a")
    report["all_link_texts"] = sorted({a.get_text(strip=True) for a in links if a.get_text(strip=True)})
    report["all_link_hrefs_sample"] = [a.get("href") for a in links[:40] if a.get("href")]

    # Look for anything that resembles a budget-type toggle/filter
    budget_keywords = ["development", "revenue", "own fund", "db", "rb", "of", "budget"]
    for a in links:
        text_lower = a.get_text(strip=True).lower()
        if any(kw in text_lower for kw in budget_keywords):
            report["budget_type_candidates"].append({
                "text": a.get_text(strip=True),
                "href": a.get("href"),
            })

    # Table structure -- if the site changed from <table> to <div>-based
    # grids, table_count will come back 0 even though data exists.
    tables = soup.find_all("table")
    report["table_count"] = len(tables)
    report["table_row_counts"] = [len(t.find_all("tr")) for t in tables]

    # Form field names -- APP search is usually a form POST; if field
    # names changed, the crawler's params dict silently gets ignored.
    inputs = soup.find_all(["input", "select"])
    report["form_field_names"] = sorted({i.get("name") for i in inputs if i.get("name")})

    if report["table_count"] == 0:
        report["notes"].append(
            "No <table> elements found at all -- page may now render "
            "results via JavaScript/AJAX, or the URL/params no longer "
            "return a results view (e.g. redirected to a plain search form)."
        )
    if not report["budget_type_candidates"]:
        report["notes"].append(
            "No link text matched budget-type keywords (development / "
            "revenue / own fund / db / rb / of) -- the exact-text match "
            "the crawler relies on ('DB'/'RB'/'OF') is very likely stale. "
            "Check all_link_texts for the current real labels."
        )

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    log.info("Diagnostic complete. See %s and %s", REPORT_PATH, RAW_HTML_PATH)
    log.info("Link texts found: %s", report["all_link_texts"][:20])
    log.info("Table count: %d", report["table_count"])
    log.info("Budget-type candidates: %s", report["budget_type_candidates"])


if __name__ == "__main__":
    diagnose()