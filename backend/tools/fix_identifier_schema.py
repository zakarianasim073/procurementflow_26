from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.database import get_sync_engine


def main() -> None:
    engine = get_sync_engine()
    with engine.begin() as conn:
        before = {
            "award_rows": conn.execute(text("SELECT COUNT(*) FROM award_records_v2")).scalar_one(),
            "bad_award_tender_ids": conn.execute(text(
                "SELECT COUNT(*) FROM award_records_v2 WHERE tender_id IS NOT NULL AND tender_id !~ '^[0-9]{5,12}$'"
            )).scalar_one(),
            "app_lifecycle_tender_ids": conn.execute(text(
                "SELECT COUNT(*) FROM procurement_lifecycle WHERE data_source = 'app_only' AND tender_id IS NOT NULL"
            )).scalar_one(),
        }

        conn.execute(text("""
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS tender_id VARCHAR(100);
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS estimated_amount_bdt DOUBLE PRECISION DEFAULT 0;
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS agency_confidence DOUBLE PRECISION DEFAULT 0;
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS procuring_entity VARCHAR(500);
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS office VARCHAR(300);
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS location VARCHAR(150);
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'egp';
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS raw_data JSON;
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS discount_pct DOUBLE PRECISION;
            ALTER TABLE award_records_v2 ADD COLUMN IF NOT EXISTS npp_ratio DOUBLE PRECISION;
        """))

        conn.execute(text("""
            UPDATE award_records_v2
            SET tender_id = NULL
            WHERE tender_id IS NOT NULL AND tender_id !~ '^[0-9]{5,12}$'
        """))
        conn.execute(text("""
            UPDATE award_records_v2
            SET tender_id = source_tender_id
            WHERE (tender_id IS NULL OR tender_id = '')
              AND source_tender_id ~ '^[0-9]{5,12}$'
        """))
        conn.execute(text("""
            UPDATE procurement_lifecycle
            SET tender_id = NULL
            WHERE data_source = 'app_only'
        """))
        conn.execute(text("""
            UPDATE procurement_lifecycle pl
            SET tender_id = aw.tender_id
            FROM award_records_v2 aw
            WHERE pl.data_source IN ('matched', 'ec_only')
              AND pl.package_no = aw.package_no
              AND COALESCE(pl.winner, '') = COALESCE(aw.contractor_name, '')
              AND COALESCE(pl.award_date, '') = COALESCE(aw.award_date, '')
              AND aw.tender_id ~ '^[0-9]{5,12}$'
        """))
        for table in ("eexperience_completed", "ecms_ongoing"):
            conn.execute(text(f"""
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tender_ref_no VARCHAR(300);
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS package_name TEXT;
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS name_of_work TEXT;
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS ministry_division VARCHAR(300);
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS organization_name VARCHAR(300);
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS pe_name VARCHAR(300);
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS procurement_nature VARCHAR(100);
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS work_category VARCHAR(200);
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS contract_no VARCHAR(200);
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS physical_progress_pct DOUBLE PRECISION DEFAULT 0;
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS financial_progress_pct DOUBLE PRECISION DEFAULT 0;
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS physical_progress_date VARCHAR(20);
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS financial_progress_date VARCHAR(20);
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS is_jvca BOOLEAN;
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS remarks TEXT;
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS comments_by_pe TEXT;
            """))
            conn.execute(text(f"""
                UPDATE {table}
                SET tender_id = NULL
                WHERE tender_id IS NOT NULL AND tender_id !~ '^[0-9]{{5,12}}$'
            """))
            conn.execute(text(f"""
                UPDATE {table} ee
                SET procurement_tender_id = pt.id
                FROM procurement_tenders pt
                WHERE ee.package_no IS NOT NULL
                  AND pt.package_no IS NOT NULL
                  AND lower(trim(ee.package_no)) = lower(trim(pt.package_no))
            """))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_tender_package ON {table} (tender_id, package_no)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_arv2_tender_id ON award_records_v2 (tender_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_arv2_agency_date ON award_records_v2 (agency_code, award_date)"))

        after = {
            "award_rows": conn.execute(text("SELECT COUNT(*) FROM award_records_v2")).scalar_one(),
            "bad_award_tender_ids": conn.execute(text(
                "SELECT COUNT(*) FROM award_records_v2 WHERE tender_id IS NOT NULL AND tender_id !~ '^[0-9]{5,12}$'"
            )).scalar_one(),
            "award_numeric_tender_ids": conn.execute(text(
                "SELECT COUNT(*) FROM award_records_v2 WHERE tender_id ~ '^[0-9]{5,12}$'"
            )).scalar_one(),
            "app_lifecycle_tender_ids": conn.execute(text(
                "SELECT COUNT(*) FROM procurement_lifecycle WHERE data_source = 'app_only' AND tender_id IS NOT NULL"
            )).scalar_one(),
            "award_lifecycle_numeric_tender_ids": conn.execute(text(
                "SELECT COUNT(*) FROM procurement_lifecycle WHERE data_source IN ('matched', 'ec_only') AND tender_id ~ '^[0-9]{5,12}$'"
            )).scalar_one(),
            "eexperience_bad_tender_ids": conn.execute(text(
                "SELECT COUNT(*) FROM eexperience_completed WHERE tender_id IS NOT NULL AND tender_id !~ '^[0-9]{5,12}$'"
            )).scalar_one(),
            "eexperience_linked_by_package": conn.execute(text(
                "SELECT COUNT(*) FROM eexperience_completed WHERE procurement_tender_id IS NOT NULL"
            )).scalar_one(),
            "ecms_ongoing_linked_by_package": conn.execute(text(
                "SELECT COUNT(*) FROM ecms_ongoing WHERE procurement_tender_id IS NOT NULL"
            )).scalar_one(),
        }

    print(json.dumps({"before": before, "after": after}, indent=2))


if __name__ == "__main__":
    main()
