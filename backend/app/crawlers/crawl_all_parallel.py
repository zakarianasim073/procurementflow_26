# crawler/crawl_all_parallel.py
"""
Parallel Awards + Opening Reports Crawler
Run: python crawler/crawl_all_parallel.py --all
     python crawler/crawl_all_parallel.py --remaining
"""
import argparse, json, logging, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import httpx

from egp_crawler import EGPCrawler, OpeningReportExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parallel-crawler")

AWARDS_DIR = Path("crawl_output/Award")
OPENING_DIR = Path("crawl_output/OpeningReports")
AWARDS_DIR.mkdir(parents=True, exist_ok=True)
OPENING_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT = AWARDS_DIR / "_checkpoint.json"

def load_checkpoint() -> set:
    if CHECKPOINT.exists():
        return set(json.loads(CHECKPOINT.read_text()).get("done", []))
    return set()

def save_checkpoint(done: set):
    CHECKPOINT.write_text(json.dumps({"done": sorted(done)}, indent=2))

def crawl_agency(agency: str) -> Tuple[str, int, int]:
    """Crawl awards + opening reports for one agency."""
    crawler = EGPCrawler()

    # Awards
    awards = []
    try:
        # Use NOA search
        html = crawler.fetch_noa_page(agency, page=1)
        if html:
            awards = crawler.parse_noa_page(html)
            for page in range(2, 6):  # Limit to recent pages
                html = crawler.fetch_noa_page(agency, page)
                if html:
                    awards.extend(crawler.parse_noa_page(html))
    except Exception as e:
        logger.warning(f"[{agency}] Awards crawl error: {e}")

    # Opening Reports (if archived tenders found)
    opening_reports = []
    try:
        archived = crawler.get_archived_tenders(max_pages=5)
        for tender in archived[:20]:  # Limit per agency
            report = crawler.extract_opening_report(tender.get("tender_id", ""))
            if report:
                opening_reports.append(report)
    except Exception as e:
        logger.warning(f"[{agency}] Opening reports error: {e}")

    # Save
    if awards:
        (AWARDS_DIR / f"{agency}.json").write_text(json.dumps(awards, indent=2, default=str), encoding="utf-8")
    if opening_reports:
        (OPENING_DIR / f"{agency}.json").write_text(json.dumps([r.__dict__ for r in opening_reports], indent=2, default=str), encoding="utf-8")

    return agency, len(awards), len(opening_reports)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--remaining", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    done = load_checkpoint()
    all_agencies = [a.strip() for a in """
BADC,BANGLADESH,BBA,BIWTA,BPDB,BREB,BWDB,CHIEF,COMMON,DKMP,DPHE,EDUCATION,
ENGINEERIN,EXECUTIVE,HED,INFORMATIO,LGED,MINISTRY,OFFICE,PIU,PWD,RAILWAY,
RAJUK,REB,RHD,UPGRADING,WASA,POLICE,POWER,HEALTH,LIVESTOCK,BCIC,BORDER,
CHITTAGONG PORT,CIVIL AVIATION,FOOD,BEPZA,COAST GUARD,SUGAR,FOREST,FISHERIES,
TEXTILES,FIRE SERVICE,LAND PORT,MONGLA PORT,PRINTING,MARINE ACADEMY,TEA BOARD,
FAMILY PLANNING,ANSAR,STATISTICS,ATOMIC ENERGY,SCIENCE TECHNOLOGY,MUSEUM,
KRIRA,POST TELECOM,ECONOMIC RELATIONS,MEDICAL EDUCATION,BPATC,COUNCIL
    """.strip().split(",")]

    if args.remaining:
        agencies = [a for a in all_agencies if a not in done]
    else:
        agencies = all_agencies

    logger.info(f"Starting parallel crawl: {len(agencies)} agencies, {args.workers} workers")

    start = time.time()
    total_awards = 0
    total_opening = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_agency = {executor.submit(crawl_agency, agency): agency for agency in agencies}
        for future in as_completed(future_to_agency):
            agency, awards, opening = future.result()
            done.add(agency)
            total_awards += awards
            total_opening += opening
            save_checkpoint(done)
            logger.info(f"[{agency}] Done: {awards} awards, {opening} opening reports")

    elapsed = time.time() - start
    logger.info(f"\n=== CRAWL COMPLETE in {elapsed/60:.1f} minutes ===")
    logger.info(f"Total: {total_awards} awards, {total_opening} opening reports")
    logger.info(f"Checkpoint updated with {len(done)} agencies")

if __name__ == "__main__":
    main()