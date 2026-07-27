"""Opening Report Importer Service

Imports OpeningReport crawl data from JSON files into PostgreSQL.
Reads JSON files from crawl_output/OpeningReport/JSON/
Supplements with price_bids from crawl_results.json where available.
Maps fields to the OpeningReport DB model.

Used by agent-003-tender-opening and admin data ingestion pipelines.
"""
from __future__ import annotations

import glob
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
CRAWL_ROOT = BACKEND_DIR / "crawl_output" / "OpeningReport"
JSON_DIR = CRAWL_ROOT / "JSON"
PDF_DIR = CRAWL_ROOT / "PDF"
CRAWL_RESULTS_JSON = CRAWL_ROOT / "crawl_results.json"


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%d-%b-%Y %H:%M", "%d-%b-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _clean_amount(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _extract_bidders(data: dict) -> List[dict]:
    bidders = []
    for b in data.get("bidders", []):
        bidder = {"name": b.get("name", ""), "serial": b.get("serial", 0)}
        bidders.append(bidder)

    price_bids = data.get("price_bids", [])
    if price_bids and len(price_bids) == len(bidders):
        for i, pb in enumerate(price_bids):
            bidders[i]["quoted_amount"] = _clean_amount(pb.get("quoted_amount"))
            bidders[i]["discount_pct"] = _clean_amount(pb.get("discount_pct"))
            bidders[i]["discount_amount"] = _clean_amount(pb.get("discount_amount"))
            bidders[i]["net_quoted"] = _clean_amount(pb.get("net_quoted"))
            bidders[i]["final_amount"] = _clean_amount(pb.get("net_quoted"))
            bidders[i]["status"] = "submitted"
    elif price_bids:
        pb_by_name = {pb.get("name", "").strip().lower(): pb for pb in price_bids}
        for b in bidders:
            name = b.get("name", "").strip().lower()
            pb = pb_by_name.get(name)
            if pb:
                b["quoted_amount"] = _clean_amount(pb.get("quoted_amount"))
                b["discount_pct"] = _clean_amount(pb.get("discount_pct"))
                b["discount_amount"] = _clean_amount(pb.get("discount_amount"))
                b["net_quoted"] = _clean_amount(pb.get("net_quoted"))
                b["final_amount"] = _clean_amount(pb.get("net_quoted"))
                b["status"] = "submitted"
    return bidders


def _load_crawl_results() -> dict:
    if not CRAWL_RESULTS_JSON.exists():
        logger.warning("crawl_results.json not found at %s", CRAWL_RESULTS_JSON)
        return {}
    with open(CRAWL_RESULTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    lookup = {}
    for r in data.get("results", []):
        tid = r.get("tender_id", "")
        if tid:
            lookup[tid] = r
    logger.info("Loaded %d records from crawl_results.json", len(lookup))
    return lookup


def _build_insert_rows(crawl_lookup: dict) -> List[dict]:
    if not JSON_DIR.exists():
        logger.warning("JSON dir not found: %s", JSON_DIR)
        return []
    json_files = sorted(glob.glob(str(JSON_DIR / "*.json")))
    rows = []
    skipped = 0
    enriched = 0
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
        tid = str(data.get("tender_id", "")).strip()
        if not tid:
            skipped += 1
            continue
        crawl = crawl_lookup.get(tid)
        if crawl and crawl.get("metadata", {}).get("price_bids"):
            data["price_bids"] = crawl["metadata"]["price_bids"]
            enriched += 1
        bidders = _extract_bidders(data)
        winner_name = data.get("award_winner", "")
        winner_amount = _clean_amount(data.get("award_amount"))
        winner_discount = _clean_amount(data.get("winner_discount_pct"))
        estimated = _clean_amount(data.get("estimated_cost"))
        pdf_path = str(PDF_DIR / f"{tid}.pdf") if (PDF_DIR / f"{tid}.pdf").exists() else None
        json_path = str(jf)
        rows.append({
            "id": str(uuid.uuid4()),
            "tender_id": tid,
            "opening_date": _parse_date(data.get("opening_date", "")),
            "pe_office": data.get("procuring_entity", ""),
            "agency": data.get("agency_name", ""),
            "zone": data.get("zone") or "",
            "package_work_name": data.get("lot_no", ""),
            "estimated_amount_bdt": estimated,
            "bidders": bidders,
            "has_slt": False,
            "has_alt": False,
            "winner_name": winner_name,
            "winner_amount": winner_amount,
            "winner_discount": winner_discount,
            "raw_data": data,
            "source_pdf": pdf_path,
            "source_json": json_path,
        })
    logger.info("Built %d rows (%d skipped, %d enriched)", len(rows), skipped, enriched)
    return rows


class OpeningReportImporterService:
    """Service to import opening report crawl data into PostgreSQL."""

    @staticmethod
    def _sync_db_url() -> str:
        url = settings.DATABASE_URL
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "")
        if "+aiosqlite" in url:
            url = url.replace("+aiosqlite", "")
        return url

    @classmethod
    def import_all(cls) -> Dict[str, Any]:
        """Full import pipeline."""
        logger.info("=" * 60)
        logger.info("OpeningReport Import")
        logger.info("=" * 60)

        crawl_lookup = _load_crawl_results()
        rows = _build_insert_rows(crawl_lookup)
        if not rows:
            logger.info("No rows to import. Exiting.")
            return {"inserted": 0, "updated": 0, "failed": 0, "skipped_fk": 0}

        result = cls._insert_rows_sync(rows)
        return result

    @classmethod
    def _insert_rows_sync(cls, rows: List[dict]) -> Dict[str, Any]:
        sync_url = cls._sync_db_url()
        engine = create_engine(sync_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        inserted = 0
        updated = 0
        failed = 0
        skipped_fk = 0

        try:
            result = session.execute(text("SELECT tender_id FROM opening_reports"))
            existing = {row[0] for row in result}
            logger.info("Existing opening_reports: %d", len(existing))

            result = session.execute(text("SELECT tender_id FROM tenders"))
            valid_tender_ids = {r[0] for r in result}
            logger.info("Valid tender_ids: %d", len(valid_tender_ids))

            valid_rows = [r for r in rows if r["tender_id"] in valid_tender_ids]
            skipped_fk = len(rows) - len(valid_rows)
            logger.info("Rows with valid FK: %d (%d skipped)", len(valid_rows), skipped_fk)

            for row in valid_rows:
                tid = row["tender_id"]
                bidders_json = json.dumps(row["bidders"], ensure_ascii=False, default=str)
                raw_json = json.dumps(row["raw_data"], ensure_ascii=False, default=str)

                if tid in existing:
                    session.execute(
                        text("""
                            UPDATE opening_reports SET
                                opening_date = :opening_date,
                                pe_office = :pe_office,
                                agency = :agency,
                                zone = :zone,
                                package_work_name = :package_work_name,
                                estimated_amount_bdt = :estimated_amount_bdt,
                                bidders = :bidders,
                                winner_name = :winner_name,
                                winner_amount = :winner_amount,
                                winner_discount = :winner_discount,
                                raw_data = :raw_data,
                                source_pdf = :source_pdf,
                                source_json = :source_json,
                                updated_at = NOW()
                            WHERE tender_id = :tender_id
                        """),
                        {
                            "tender_id": tid,
                            "opening_date": row["opening_date"],
                            "pe_office": row["pe_office"][:255] if row["pe_office"] else None,
                            "agency": row["agency"][:255] if row["agency"] else None,
                            "zone": (row["zone"] or "")[:100],
                            "package_work_name": row["package_work_name"],
                            "estimated_amount_bdt": row["estimated_amount_bdt"],
                            "bidders": bidders_json,
                            "winner_name": row["winner_name"][:255] if row["winner_name"] else None,
                            "winner_amount": row["winner_amount"],
                            "winner_discount": row["winner_discount"],
                            "raw_data": raw_json,
                            "source_pdf": row["source_pdf"],
                            "source_json": row["source_json"],
                        },
                    )
                    updated += 1
                else:
                    session.execute(
                        text("""
                            INSERT INTO opening_reports (
                                id, tender_id, opening_date, pe_office, agency, zone,
                                package_work_name, estimated_amount_bdt, bidders,
                                has_slt, has_alt, winner_name, winner_amount, winner_discount,
                                raw_data, source_pdf, source_json, created_at, updated_at
                            ) VALUES (
                                :id, :tender_id, :opening_date, :pe_office, :agency, :zone,
                                :package_work_name, :estimated_amount_bdt, :bidders,
                                :has_slt, :has_alt, :winner_name, :winner_amount, :winner_discount,
                                :raw_data, :source_pdf, :source_json, NOW(), NOW()
                            )
                        """),
                        {
                            "id": row["id"],
                            "tender_id": tid,
                            "opening_date": row["opening_date"],
                            "pe_office": row["pe_office"][:255] if row["pe_office"] else None,
                            "agency": row["agency"][:255] if row["agency"] else None,
                            "zone": (row["zone"] or "")[:100],
                            "package_work_name": row["package_work_name"],
                            "estimated_amount_bdt": row["estimated_amount_bdt"],
                            "bidders": bidders_json,
                            "has_slt": row["has_slt"],
                            "has_alt": row["has_alt"],
                            "winner_name": row["winner_name"][:255] if row["winner_name"] else None,
                            "winner_amount": row["winner_amount"],
                            "winner_discount": row["winner_discount"],
                            "raw_data": raw_json,
                            "source_pdf": row["source_pdf"],
                            "source_json": row["source_json"],
                        },
                    )
                    inserted += 1

            session.commit()
            logger.info("Import complete: inserted=%d updated=%d", inserted, updated)

        except Exception as e:
            session.rollback()
            logger.error("Import failed: %s", e)
            failed = len(valid_rows) - inserted - updated
            raise
        finally:
            session.close()
            engine.dispose()

        return {"inserted": inserted, "updated": updated, "failed": failed, "skipped_fk": skipped_fk}


# ── Standalone CLI ────────────────────────────────────────────────────────────

def _cli():
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = OpeningReportImporterService.import_all()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _cli()
