from __future__ import annotations

import json
import re
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from ..framework.logger import get_logger

log = get_logger("crawler.app_listings")

BASE_URL = "https://www.eprocure.gov.bd"
SEARCH_URL = f"{BASE_URL}/SearchServlet"

ALL_FYS = [
    "2014-2015", "2015-2016", "2016-2017", "2017-2018", "2018-2019",
    "2019-2020", "2020-2021", "2021-2022", "2022-2023", "2023-2024",
    "2024-2025", "2025-2026", "2026-2027",
]

BATCH_SIZE = 100
TIMEOUT = 70


def parse_listing_row(row_html: str) -> Optional[Dict[str, Any]]:
    cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.DOTALL | re.IGNORECASE)
    if len(cells) < 6:
        return None
    texts = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
    texts = [re.sub(r"\s+", " ", t) for t in texts]
    if not texts or not texts[0].isdigit():
        return None

    item: Dict[str, Any] = OrderedDict()
    item["source"] = "egp_daily"
    item["page_source"] = "search_servlet_by_fy"

    parts1 = texts[1].split(",", 1)
    item["app_id"] = parts1[0].strip()
    item["app_code"] = parts1[1].strip() if len(parts1) > 1 else ""

    parts2 = texts[2].split(",", 1) if len(texts) > 2 else ["", ""]
    item["organization"] = parts2[0].strip()
    item["procuring_entity"] = parts2[1].strip() if len(parts2) > 1 else ""

    item["district"] = texts[3] if len(texts) > 3 else ""

    parts4 = texts[4].split(",", 1) if len(texts) > 4 else ["", ""]
    item["procurement_nature"] = parts4[0].strip()
    item["project_name"] = parts4[1].strip() if len(parts4) > 1 else ""

    parts5 = texts[5].split(",", 1) if len(texts) > 5 else ["", ""]
    item["package_no"] = parts5[0].strip()
    item["title"] = parts5[1].strip() if len(parts5) > 1 else ""

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

    item["financial_year"] = ""
    item["last_updated"] = datetime.now(timezone.utc).isoformat()
    return item


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


def load_checkpoint(path: Path) -> Dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_checkpoint(path: Path, state: Dict[str, Any]) -> None:
    write_json_safe(path, state)


def save_record_jsonl(output_path: Path, fy: str, record: Dict[str, Any]) -> None:
    entry = {
        "source": "eprocure_app_listing",
        "raw_data": record,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")


def discover_total_pages(client: httpx.Client, fy: str) -> int:
    r = client.post(
        SEARCH_URL,
        data={
            "action": "Search", "departmentId": "0", "office": "",
            "financialYear": fy, "budgetType": "", "procNature": "",
            "procType": "", "pageNo": "1", "size": "50",
        },
        timeout=TIMEOUT,
    )
    tp_m = re.search(r'<input[^>]*id="totalPages"[^>]*value="(\d+)"', r.text)
    return int(tp_m.group(1)) if tp_m else 0


def crawl_fy_listings(
    fy: str,
    client: httpx.Client,
    output_dir: Path,
    checkpoint_path: Path,
    max_pages: Optional[int] = None,
    jsonl_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    fy_dir = output_dir / f"FY_{fy}"
    fy_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = load_checkpoint(checkpoint_path)
    fy_key = f"FY_{fy}"

    if checkpoint.get(fy_key) == "done":
        merged = output_dir / f"FY_{fy}.json"
        if merged.exists():
            data = json.loads(merged.read_text(encoding="utf-8"))
            log.info("fy_already_done", fy=fy, count=len(data))
            return data

    total_pages = discover_total_pages(client, fy)
    if total_pages == 0:
        log.warning("fy_zero_pages", fy=fy)
        return []

    pages_to_crawl = min(total_pages, max_pages) if max_pages else total_pages
    log.info("fy_start", fy=fy, total_pages=total_pages, to_crawl=pages_to_crawl)

    page = int(checkpoint.get(f"{fy_key}_page", 1))
    batch_idx = int(checkpoint.get(f"{fy_key}_batch", 0))
    all_records: List[Dict[str, Any]] = []

    while page <= pages_to_crawl:
        batch_end = min(page + BATCH_SIZE - 1, pages_to_crawl)
        batch_data: List[Dict[str, Any]] = []

        for p in range(page, batch_end + 1):
            try:
                if not client.cookies:
                    client.get(BASE_URL)
                r = client.post(
                    SEARCH_URL,
                    data={
                        "action": "Search", "departmentId": "0", "office": "",
                        "financialYear": fy, "budgetType": "", "procNature": "",
                        "procType": "", "pageNo": str(p), "size": "50",
                    },
                    timeout=TIMEOUT,
                )
                if r.status_code == 200 and len(r.text) > 200:
                    rows = re.findall(r"<tr[^>]*>.*?</tr>", r.text, re.DOTALL | re.IGNORECASE)
                    for row_html in rows:
                        item = parse_listing_row(row_html)
                        if item:
                            item["financial_year"] = fy
                            batch_data.append(item)
                            if jsonl_path:
                                save_record_jsonl(jsonl_path, fy, item)
            except Exception as e:
                log.error("fy_page_error", fy=fy, page=p, error=str(e))
            time.sleep(0.1)

        if batch_data:
            batch_idx += 1
            bf = fy_dir / f"batch_{batch_idx:04d}.json"
            write_json_safe(bf, batch_data)
            all_records.extend(batch_data)

        cp = load_checkpoint(checkpoint_path)
        cp[f"{fy_key}_page"] = batch_end + 1
        cp[f"{fy_key}_batch"] = batch_idx
        save_checkpoint(checkpoint_path, cp)

        log.info("fy_progress", fy=fy, page=page, end=batch_end, total=pages_to_crawl, batch=batch_idx, records=len(batch_data))
        page = batch_end + 1

    merged_fp = output_dir / f"FY_{fy}.json"
    write_json_safe(merged_fp, all_records, indent=2)

    cp = load_checkpoint(checkpoint_path)
    cp[fy_key] = "done"
    save_checkpoint(checkpoint_path, cp)

    log.info("fy_complete", fy=fy, count=len(all_records))
    return all_records


def crawl_all_fys(
    output_dir: Path,
    start_fy: Optional[str] = None,
    max_pages: Optional[int] = None,
    jsonl_path: Optional[Path] = None,
    client: Optional[httpx.Client] = None,
) -> Dict[str, int]:
    fys = ALL_FYS
    if start_fy:
        fys = [fy for fy in fys if fy >= start_fy]

    close_client = client is None
    if client is None:
        client = httpx.Client(verify=True, follow_redirects=True, timeout=TIMEOUT)
        client.get(BASE_URL)

    checkpoint_path = output_dir / "_checkpoint.json"
    results: Dict[str, int] = {}

    try:
        for fy in fys:
            records = crawl_fy_listings(fy, client, output_dir, checkpoint_path, max_pages, jsonl_path)
            results[fy] = len(records)
    finally:
        if close_client:
            client.close()

    return results
