"""
Import All APP Data to PostgreSQL 17

Crawls APP listings via SearchServlet across ALL Financial Years,
saves to JSONL, then imports directly to PG17.

Usage:
    python backend/crawler/import_all_app.py
    python backend/crawler/import_all_app.py --fy 2025-2026
    python backend/crawler/import_all_app.py --fy 2025-2026 --max-pages 100
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# PG17 connection
DB_HOST = "localhost"
DB_PORT = 5433
DB_NAME = "procureflow_bd"
DB_USER = "postgres"
DB_PASS = "procurementflow"

OUTPUT_DIR = Path("output/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE = OUTPUT_DIR / "raw_app_listings.jsonl"

BASE_URL = "https://www.eprocure.gov.bd"

ALL_FYS = [
    "2014-2015", "2015-2016", "2016-2017", "2017-2018", "2018-2019",
    "2019-2020", "2020-2021", "2021-2022", "2022-2023", "2023-2024",
    "2024-2025", "2025-2026", "2026-2027",
]


def save_record(fy, record):
    """Save a single record to JSONL file."""
    entry = {
        "source": "eprocure_app_listing",
        "raw_data": {
            "financial_year": fy,
            "app_id": record.get("app_id"),
            "app_code": record.get("app_code"),
            "organization": record.get("organization"),
            "procuring_entity": record.get("procuring_entity"),
            "district": record.get("district"),
            "procurement_nature": record.get("procurement_nature"),
            "project_name": record.get("project_name"),
            "package_no": record.get("package_no"),
            "description": record.get("description"),
            "estimated_cost_bdt": record.get("estimated_cost_bdt"),
            "procurement_method": record.get("procurement_method"),
        },
        "crawled_at": datetime.utcnow().isoformat(),
    }
    with open(JSONL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")


def parse_row(row_html, fy):
    """Parse a single <tr> from SearchServlet into a record dict."""
    cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.DOTALL | re.IGNORECASE)
    if len(cells) < 6:
        return None
    texts = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
    texts = [re.sub(r"\s+", " ", t) for t in texts]
    if not texts or not texts[0].isdigit():
        return None

    parts1 = texts[1].split(",", 1)
    parts2 = texts[2].split(",", 1) if len(texts) > 2 else ["", ""]
    parts4 = texts[4].split(",", 1) if len(texts) > 4 else ["", ""]
    parts5 = texts[5].split(",", 1) if len(texts) > 5 else ["", ""]

    rec = {
        "app_id": parts1[0].strip(),
        "app_code": parts1[1].strip() if len(parts1) > 1 else "",
        "organization": parts2[0].strip(),
        "procuring_entity": parts2[1].strip() if len(parts2) > 1 else "",
        "district": texts[3] if len(texts) > 3 else "",
        "procurement_nature": parts4[0].strip(),
        "project_name": parts4[1].strip() if len(parts4) > 1 else "",
        "package_no": parts5[0].strip(),
        "description": parts5[1].strip() if len(parts5) > 1 else "",
        "estimated_cost_bdt": None,
        "procurement_method": None,
    }
    if len(texts) > 6:
        amt_m = re.search(r"([\d,]+\.?\d*)", texts[6])
        if amt_m:
            try:
                rec["estimated_cost_bdt"] = float(amt_m.group(1).replace(",", ""))
            except ValueError:
                pass
        meth_m = re.search(r",\s*(\w+)", texts[6])
        if meth_m:
            rec["procurement_method"] = meth_m.group(1)
    return rec


def crawl_fy(fy, client, max_pages=None):
    """Crawl a single Financial Year. Returns count of records saved."""
    # Get first page to discover total pages
    r = client.post(
        f"{BASE_URL}/SearchServlet",
        data={
            "action": "Search", "departmentId": "0", "office": "",
            "financialYear": fy, "budgetType": "", "procNature": "",
            "procType": "", "pageNo": "1", "size": "50",
        },
        timeout=70,
    )
    tp_m = re.search(r'<input[^>]*id="totalPages"[^>]*value="(\d+)"', r.text)
    total_pages = int(tp_m.group(1)) if tp_m else 0
    if total_pages == 0:
        print(f"  [SKIP] {fy}: 0 pages")
        return 0

    pages_to_crawl = min(total_pages, max_pages) if max_pages else total_pages
    print(f"  {fy}: {total_pages} pages total, crawling {pages_to_crawl}")

    saved = 0
    for page in range(1, pages_to_crawl + 1):
        try:
            r = client.post(
                f"{BASE_URL}/SearchServlet",
                data={
                    "action": "Search", "departmentId": "0", "office": "",
                    "financialYear": fy, "budgetType": "", "procNature": "",
                    "procType": "", "pageNo": str(page), "size": "50",
                },
                timeout=70,
            )
            if r.status_code == 200 and len(r.text) > 200:
                rows = re.findall(r"<tr[^>]*>.*?</tr>", r.text, re.DOTALL | re.IGNORECASE)
                for row_html in rows:
                    rec = parse_row(row_html, fy)
                    if rec:
                        save_record(fy, rec)
                        saved += 1
        except Exception as e:
            print(f"    ERROR {fy} p{page}: {e}")
        time.sleep(0.05)

        if page % 500 == 0:
            print(f"    [{fy}] p{page}/{pages_to_crawl} ({saved} records)")

    print(f"  [DONE] {fy}: {saved} records saved")
    return saved


def import_to_pg():
    """Import JSONL file to PostgreSQL 17."""
    if not JSONL_FILE.exists():
        print(f"No data file found: {JSONL_FILE}")
        return 0

    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed. Skipping DB import.")
        return 0

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS,
    )
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw_app_listings (
            id SERIAL PRIMARY KEY,
            source TEXT,
            raw_data JSONB,
            crawled_at TIMESTAMP DEFAULT now()
        )
    """)
    conn.commit()

    count = 0
    with open(JSONL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cur.execute(
                "INSERT INTO raw_app_listings (source, raw_data, crawled_at) VALUES (%s, %s, %s)",
                (rec["source"], json.dumps(rec["raw_data"], default=str), rec["crawled_at"]),
            )
            count += 1
            if count % 10000 == 0:
                conn.commit()
                print(f"    Imported {count} records...")
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Imported {count} records to raw_app_listings")
    return count


def main():
    parser = argparse.ArgumentParser(description="Import ALL APP data to PG17")
    parser.add_argument("--fy", type=str, default=None, help="Single FY to crawl (e.g. 2025-2026)")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages per FY")
    parser.add_argument("--db-only", action="store_true", help="Only import existing JSONL to DB, skip crawl")
    args = parser.parse_args()

    if args.db_only:
        count = import_to_pg()
        print(f"\nTotal imported: {count}")
        return

    # Crawl
    client = httpx.Client(verify=True, follow_redirects=True, timeout=70)
    client.get(BASE_URL)

    fys = [args.fy] if args.fy else ALL_FYS
    total = 0
    for fy in fys:
        saved = crawl_fy(fy, client, max_pages=args.max_pages)
        total += saved
        print(f"  Running total: {total:,d} records\n")

    client.close()
    print(f"\nCrawl complete! {total:,d} total records in {JSONL_FILE}")

    # Import to PG17
    imported = import_to_pg()
    print(f"\nTotal imported to PG17: {imported}")


if __name__ == "__main__":
    main()
