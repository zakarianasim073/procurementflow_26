#!/usr/bin/env python
"""
Combined APP crawler module for Bangladesh e-GP.

Includes:

1) SearchServlet APP_BY_FY listing crawler ("coarse" APP):
   - Crawls Annual Procurement Plan (APP) listings per Financial Year.
   - Output under: backend/crawl_output/APP_BY_FY/FY_<YYYY-YYYY>/
     with batch_XXXX.json and merged FY_<YYYY-YYYY>.json.

2) Framework-based APPCrawler ("rich" APP):
   - Uses DeptTree.jsp?operation=AdvAPPSearch and ViewPackageDetail links.
   - Extracts full APP package details + lot breakdowns.
   - Saves JSON records via save_raw_record("raw_app_packages", "eprocure_app", data).

Usage examples (from backend directory):

    # Only APP listings by FY (SearchServlet)
    python -m backend.crawler.app_crawler_combined --listings --start-fy 2019-2020

    # Only rich APP packages via framework
    python -m backend.crawler.app_crawler_combined --packages --max-pages-per-budget 5

    # Both layers
    python -m backend.crawler.app_crawler_combined --listings --packages

"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import structlog

# ---------- Common config ----------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT

BASE_URL = "https://www.eprocure.gov.bd"

LISTINGS_OUTPUT_DIR = BACKEND_DIR / "backend" / "crawl_output" / "APP_BY_FY"
LISTINGS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LISTINGS_FYS = [
    "2014-2015",
    "2015-2016",
    "2016-2017",
    "2017-2018",
    "2018-2019",
    "2019-2020",
    "2020-2021",
    "2021-2022",
    "2022-2023",
    "2023-2024",
    "2024-2025",
    "2025-2026",
    "2026-2027",
]

LISTINGS_CHECKPOINT_FILE = LISTINGS_OUTPUT_DIR / "_checkpoint.json"
LISTINGS_BATCH_SIZE = 100
LISTINGS_TIMEOUT = 70

logger = structlog.get_logger()


# ================================================================
# 1. SearchServlet-based APP_BY_FY listing crawler
# ================================================================

def write_json_safe(path: Path, data: Any, *, indent: Optional[int] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=indent, default=str)
    for attempt in range(3):
        try:
            path.write_text(payload, encoding="utf-8")
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1.0)


def load_checkpoint() -> Dict[str, Any]:
    if LISTINGS_CHECKPOINT_FILE.exists():
        return json.loads(LISTINGS_CHECKPOINT_FILE.read_text(encoding="utf-8"))
    return {}


def save_checkpoint(state: Dict[str, Any]) -> None:
    write_json_safe(LISTINGS_CHECKPOINT_FILE, state)


def parse_listing_row(row_html: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single <tr> row from SearchServlet APP listing into a record.
    """
    cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.DOTALL | re.IGNORECASE)
    if len(cells) < 6:
        return None

    texts = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
    texts = [re.sub(r"\s+", " ", t) for t in texts]

    # First cell is S. No (should be numeric)
    if not texts or not texts[0].isdigit():
        return None

    item: Dict[str, Any] = OrderedDict()
    item["source"] = "egp_daily"
    item["page_source"] = "search_servlet_by_fy"

    # Col 1: APP ID + APP Code
    parts1 = texts[1].split(",", 1)
    item["app_id"] = parts1[0].strip()
    item["app_code"] = parts1[1].strip() if len(parts1) > 1 else ""

    # Col 2: Organization + Procuring Entity
    parts2 = texts[2].split(",", 1) if len(texts) > 2 else ["", ""]
    item["organization"] = parts2[0].strip()
    item["procuring_entity"] = parts2[1].strip() if len(parts2) > 1 else ""

    # Col 3: District
    item["district"] = texts[3] if len(texts) > 3 else ""

    # Col 4: Procurement Nature + Project Name
    parts4 = texts[4].split(",", 1) if len(texts) > 4 else ["", ""]
    item["procurement_nature"] = parts4[0].strip()
    item["project_name"] = parts4[1].strip() if len(parts4) > 1 else ""

    # Col 5: Package No + Title
    parts5 = texts[5].split(",", 1) if len(texts) > 5 else ["", ""]
    item["package_no"] = parts5[0].strip()
    item["title"] = parts5[1].strip() if len(parts5) > 1 else ""

    # Col 6: Estimated Cost + Method (if present)
    if len(texts) > 6:
        amt_m = re.search(r"([\d,]+\.?\d*)", texts[6])
        if amt_m:
            try:
                item["estimated_cost_bdt"] = float(amt_m.group(1).replace(",", ""))
            except ValueError:
                item["estimated_cost_bdt"] = None
        meth_m = re.search(r",\s*(\w+)", texts[6])
        if meth_m:
            item["procurement_method"] = meth_m.group(1)

    item["financial_year"] = ""  # filled in crawl_fy
    item["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return item


def crawl_fy_listings(fy: str, client: httpx.Client) -> List[Dict[str, Any]]:
    """
    Crawl APP listings for a single Financial Year via SearchServlet, saving
    batches under APP_BY_FY/FY_<fy>/ and merging into FY_<fy>.json.

    Returns all records for that FY.
    """
    fy_dir = LISTINGS_OUTPUT_DIR / f"FY_{fy}"
    fy_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = load_checkpoint()
    fy_key = f"FY_{fy}"

    # If FY marked done, reuse merged file
    if checkpoint.get(fy_key) == "done":
        merged = LISTINGS_OUTPUT_DIR / f"FY_{fy}.json"
        if merged.exists():
            data = json.loads(merged.read_text(encoding="utf-8"))
            print(f"  [SKIP] {fy} already done ({len(data)} records)", flush=True)
            return data

    # Discover total pages
    r = client.post(
        f"{BASE_URL}/SearchServlet",
        data={
            "action": "Search",
            "departmentId": "0",
            "office": "",
            "financialYear": fy,
            "budgetType": "",
            "procNature": "",
            "procType": "",
            "pageNo": "1",
            "size": "50",
        },
        timeout=LISTINGS_TIMEOUT,
    )
    tp_m = re.search(r'<input[^>]*id="totalPages"[^>]*value="(\d+)"', r.text)
    total_pages = int(tp_m.group(1)) if tp_m else 0
    if total_pages == 0:
        print(f"  [WARN] {fy}: 0 pages", flush=True)
        return []

    print(f"  {fy}: {total_pages} pages", flush=True)

    page = int(checkpoint.get(f"{fy_key}_page", 1))
    batch_idx = int(checkpoint.get(f"{fy_key}_batch", 0))

    while page <= total_pages:
        batch_end = min(page + LISTINGS_BATCH_SIZE - 1, total_pages)
        batch_data: List[Dict[str, Any]] = []

        for p in range(page, batch_end + 1):
            try:
                if not client.cookies:
                    client.get(BASE_URL)
                r = client.post(
                    f"{BASE_URL}/SearchServlet",
                    data={
                        "action": "Search",
                        "departmentId": "0",
                        "office": "",
                        "financialYear": fy,
                        "budgetType": "",
                        "procNature": "",
                        "procType": "",
                        "pageNo": str(p),
                        "size": "50",
                    },
                    timeout=LISTINGS_TIMEOUT,
                )
                if r.status_code == 200 and len(r.text) > 200:
                    rows = re.findall(r"<tr[^>]*>.*?</tr>", r.text, re.DOTALL | re.IGNORECASE)
                    for row_html in rows:
                        item = parse_listing_row(row_html)
                        if item:
                            item["financial_year"] = fy
                            batch_data.append(item)
            except Exception as e:
                print(f"    ERROR {fy} p{p}: {e}", flush=True)
            time.sleep(0.1)

        if batch_data:
            batch_idx += 1
            bf = fy_dir / f"batch_{batch_idx:04d}.json"
            write_json_safe(bf, batch_data)
        # update checkpoint
        cp = load_checkpoint()
        cp[f"{fy_key}_page"] = batch_end + 1
        cp[f"{fy_key}_batch"] = batch_idx
        save_checkpoint(cp)

        pct = (batch_end / total_pages) * 100
        print(
            f"    [{fy}] p{page}-{batch_end}/{total_pages} ({pct:.0f}%), "
            f"batch {batch_idx} ({len(batch_data)} records)",
            flush=True,
        )
        page = batch_end + 1

    # Merge
    all_data: List[Dict[str, Any]] = []
    for bf in sorted(fy_dir.glob("batch_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        all_data.extend(json.loads(bf.read_text(encoding="utf-8")))
    merged_fp = LISTINGS_OUTPUT_DIR / f"FY_{fy}.json"
    write_json_safe(merged_fp, all_data, indent=2)

    cp = load_checkpoint()
    cp[fy_key] = "done"
    save_checkpoint(cp)

    print(f"  [DONE] {fy}: {len(all_data)} records saved", flush=True)
    return all_data


def crawl_app_listings_by_fy(start_fy: Optional[str] = None) -> None:
    """
    Run SearchServlet-based APP listings crawler across FYs (2014-2015 .. 2026-2027),
    or from a given start_fy.
    """
    fys = LISTINGS_FYS
    if start_fy:
        fys = [fy for fy in fys if fy >= start_fy]

    client = httpx.Client(verify=True, follow_redirects=True, timeout=LISTINGS_TIMEOUT)
    client.get(BASE_URL)

    total_all = 0
    for fy in fys:
        records = crawl_fy_listings(fy, client)
        total_all += len(records)
        print(f"  Running total: {total_all:,d} records", flush=True)

    client.close()
    print("\n" + "=" * 60, flush=True)
    print(f"Crawl complete! {total_all:,d} total listing records in {LISTINGS_OUTPUT_DIR}", flush=True)


# ================================================================
# 2. Framework-based APPCrawler (AdvAPPSearch / ViewPackageDetail)
# ================================================================

# These imports assume your framework lives under backend.crawler.framework
from backend.crawler.framework.base_crawler import BaseCrawler
from backend.crawler.framework.extractor import (
    extract_label_value_map,
    get_field,
    extract_table_rows,
)
from backend.crawler.framework.storage import save_raw_record
from backend.crawler.framework.config import BASE_URL as FW_BASE_URL
from backend.crawler.framework.retry import with_retry


class APPCrawler(BaseCrawler):
    """
    Rich APP crawler using Advanced APP Search (DeptTree.jsp?operation=AdvAPPSearch)
    and ViewPackageDetail pages.

    Outputs JSON records to raw_app_packages via save_raw_record().
    """

    name = "app_packages"
    START_URL = FW_BASE_URL + "DeptTree.jsp?operation=AdvAPPSearch"

    async def initialize(self):
        self.context = await self.browser_manager.get_context()

    @with_retry
    async def _goto(self, page, url: str):
        await page.goto(url, wait_until="networkidle")

    def _pkg_id(self, href: str) -> str:
        m = re.search(r"pkgId=(\d+)", href)
        return m.group(1) if m else ""

    async def run(self, max_pages_per_budget: int = 2):
        self._log_start()
        items_total = 0
        try:
            await self.initialize()
            page = await self.context.new_page()
            await self._goto(page, self.START_URL)

            # Discover budget-type APP list links: DB, RB, OF
            links = await page.query_selector_all("a")
            budget_links: List[str] = []
            for link in links:
                href = await link.get_attribute("href")
                text = (await link.inner_text()).strip()
                if href and "StdSearch" in href and text in ("DB", "RB", "OF"):
                    budget_links.append(href)

            for blink in budget_links:
                list_page = await self.context.new_page()
                url = blink if blink.startswith("http") else FW_BASE_URL + blink.lstrip("/")
                await self._goto(list_page, url)

                page_count = 0
                while page_count < max_pages_per_budget:
                    # Find package links on this list page
                    pkg_links = await list_page.query_selector_all("a[href*='ViewPackageDetail']")
                    hrefs = [await l.get_attribute("href") for l in pkg_links]

                    for href in hrefs:
                        if not href:
                            continue
                        try:
                            detail_page = await self.context.new_page()
                            full_url = href if href.startswith("http") else FW_BASE_URL + href.lstrip("/")
                            await self._goto(detail_page, full_url)

                            kv = await extract_label_value_map(detail_page)
                            lot_rows = await extract_table_rows(detail_page, "table")
                            lots = [
                                {
                                    "lot_no": r[0],
                                    "lot_description": r[1],
                                    "qty": r[2],
                                    "unit": r[3],
                                    "estimated_cost_bdt": r[4],
                                }
                                for r in lot_rows
                                if len(r) >= 5 and r[0].strip().isdigit()
                            ]

                            data = {
                                "app_id": get_field(kv, "APP ID"),
                                "pkg_id": self._pkg_id(href),
                                "app_code": get_field(kv, "APP Code"),
                                "financial_year": get_field(kv, "Financial Year"),
                                "ministry": get_field(kv, "Ministry"),
                                "organization": get_field(kv, "Organization"),
                                "pe_office": get_field(kv, "PE Office and Code"),
                                "budget_type": get_field(kv, "Budget Type"),
                                "project_name": get_field(kv, "Project Name"),
                                "district": get_field(kv, "District"),
                                "package_no": get_field(kv, "Package No"),
                                "package_description": get_field(kv, "Package Description"),
                                "package_estimated_cost_bdt": get_field(kv, "Package Estimated Cost"),
                                "category": get_field(kv, "Category"),
                                "procurement_method": get_field(kv, "Procurement Method"),
                                "procurement_type": get_field(kv, "Procurement Type"),
                                "source_of_fund": get_field(kv, "Source of Fund"),
                                "exp_advertisement_date": get_field(kv, "Expected Date of Advertisement"),
                                "exp_contract_signing_date": get_field(kv, "Expected Date of Signing of Contract"),
                                "exp_completion_date": get_field(kv, "Expected Date of Completion of Contract"),
                                "total_time_to_signing_days": get_field(kv, "Total Time to Contract Signing"),
                                "lots": lots,
                                "raw": kv,
                            }

                            if data.get("app_id"):
                                save_raw_record("raw_app_packages", "eprocure_app", data)
                                items_total += 1

                            await detail_page.close()
                            await asyncio.sleep(self.rate_limit)
                        except Exception as e:
                            logger.error("app_item_failed", error=str(e), href=href)

                    self._log_progress(page_count + 1, items_total)

                    # Pagination: click 'Next' if available
                    next_btn = await list_page.query_selector("a:has-text('Next')")
                    if next_btn:
                        await next_btn.click()
                        await list_page.wait_for_load_state("networkidle")
                        page_count += 1
                    else:
                        break

                await list_page.close()

            self._log_finish("success")
        except Exception as e:
            logger.error("app_crawl_failed", error=str(e))
            self._log_finish("failed", str(e))
        finally:
            await self.finish()


# ================================================================
# 3. Combined CLI entrypoint
# ================================================================

def run_rich_app_packages(max_pages_per_budget: int) -> None:
    """
    Run APPCrawler via the framework (rich APP packages).
    """
    async def _runner():
        crawler = APPCrawler()
        await crawler.run(max_pages_per_budget=max_pages_per_budget)

    asyncio.run(_runner())


def run_all_app_crawls(start_fy: Optional[str], max_pages_per_budget: int) -> None:
    """
    Run both APP listing crawler (SearchServlet by FY) and APPCrawler
    (package detail) in sequence.
    """
    print("\n" + "=" * 60)
    print("PHASE A: APP listings by Financial Year (SearchServlet)")
    print("=" * 60)
    crawl_app_listings_by_fy(start_fy=start_fy)

    print("\n" + "=" * 60)
    print("PHASE B: APP packages via AdvAPPSearch / ViewPackageDetail")
    print("=" * 60)
    run_rich_app_packages(max_pages_per_budget=max_pages_per_budget)


def main():
    parser = argparse.ArgumentParser(description="Combined APP crawler (listings + packages)")
    parser.add_argument(
        "--listings",
        action="store_true",
        help="Run SearchServlet APP listings crawl by FY (APP_BY_FY).",
    )
    parser.add_argument(
        "--packages",
        action="store_true",
        help="Run APPCrawler (rich APP packages via AdvAPPSearch).",
    )
    parser.add_argument(
        "--start-fy",
        type=str,
        default=None,
        help="Optional: start APP listings from this FY (e.g. 2019-2020).",
    )
    parser.add_argument(
        "--max-pages-per-budget",
        type=int,
        default=2,
        help="Max list pages per budget type (DB/RB/OF) for APPCrawler.",
    )

    args = parser.parse_args()

    # Default: if neither flag is set, run both
    run_listings = args.listings or (not args.listings and not args.packages)
    run_packages = args.packages or (not args.listings and not args.packages)

    if run_listings and run_packages:
        run_all_app_crawls(start_fy=args.start_fy, max_pages_per_budget=args.max_pages_per_budget)
    elif run_listings:
        crawl_app_listings_by_fy(start_fy=args.start_fy)
    elif run_packages:
        run_rich_app_packages(max_pages_per_budget=args.max_pages_per_budget)


if __name__ == "__main__":
    main()
