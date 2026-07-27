# crawler/crawl_all_parallel.py
"""
Parallel Awards + Opening Reports Crawler
Plus optional APP crawl across all Financial Years.

Run:
  python crawler/crawl_all_parallel.py --all
  python crawler/crawl_all_parallel.py --remaining
  python crawler/crawl_all_parallel.py --with-app
  python crawler/crawl_all_parallel.py --with-app --app-start-fy 2019-2020
"""

import argparse, json, logging, time, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import httpx

from egp_crawler import EGPCrawler, OpeningReportExtractor
from app_crawler import run_app_crawl  # <- new import

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parallel-crawler")

AWARDS_DIR = Path("crawl_output/Award")
OPENING_DIR = Path("crawl_output/OpeningReports")
AWARDS_DIR.mkdir(parents=True, exist_ok=True)
OPENING_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT = AWARDS_DIR / "_checkpoint.json"

# ... crawl_agency, load_checkpoint, save_checkpoint stay unchanged ...


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--remaining", action="store_true")
    parser.add_argument("--workers", type=int, default=6)

    # New flags for APP crawl
    parser.add_argument(
        "--with-app",
        action="store_true",
        help="Run APP crawl (SearchServlet, departmentId=0) across FYs before awards/opening.",
    )
    parser.add_argument(
        "--app-start-fy",
        type=str,
        default=None,
        help="Optional: start APP crawl from this FY (e.g. 2019-2020).",
    )

    args = parser.parse_args()

    # Optional APP crawl first, per initial plan
    if args.with_app:
        logger.info("Starting APP crawl via app_crawler.run_app_crawl()")
        run_app_crawl(start_fy=args.app_start_fy)
        logger.info("APP crawl complete")

    done = load_checkpoint()
    all_agencies = [
        a.strip()
        for a in """
BADC,BANGLADESH,BBA,BIWTA,BPDB,BREB,BWDB,CHIEF,COMMON,DKMP,DPHE,EDUCATION,
ENGINEERIN,EXECUTIVE,HED,INFORMATIO,LGED,MINISTRY,OFFICE,PIU,PWD,RAILWAY,
RAJUK,REB,RHD,UPGRADING,WASA,POLICE,POWER,HEALTH,LIVESTOCK,BCIC,BORDER,
CHITTAGONG PORT,CIVIL AVIATION,FOOD,BEPZA,COAST GUARD,SUGAR,FOREST,FISHERIES,
TEXTILES,FIRE SERVICE,LAND PORT,MONGLA PORT,PRINTING,MARINE ACADEMY,TEA BOARD,
FAMILY PLANNING,ANSAR,STATISTICS,ATOMIC ENERGY,SCIENCE TECHNOLOGY,MUSEUM,
KRIRA,POST TELECOM,ECONOMIC RELATIONS,MEDICAL EDUCATION,BPATC,COUNCIL
""".strip().split(",")
    ]

    if args.remaining:
        agencies = [a for a in all_agencies if a not in done]
    else:
        agencies = all_agencies

    logger.info(f"Starting parallel awards/opening crawl: {len(agencies)} agencies, {args.workers} workers")

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
    logger.info(f"\n=== AWARDS/OPENING CRAWL COMPLETE in {elapsed/60:.1f} minutes ===")
    logger.info(f"Total: {total_awards} awards, {total_opening} opening reports")
    logger.info(f"Checkpoint updated with {len(done)} agencies")


if __name__ == "__main__":
    main()