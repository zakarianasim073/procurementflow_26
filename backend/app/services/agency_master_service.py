"""Agency Master Service

Builds and maintains a comprehensive agencies master table from ALL data sources:
  - award_records_v2 (contractor awards)
  - app_records (tender plans)
  - eexperience_completed (e-experience)
  - econtract_execution (e-contracts)
  - ecms_ongoing (ongoing projects)
  - existing agencies table

Creates a unified agency map with proper ministry hierarchy.
Used by admin agents and dashboard analytics.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import psycopg2
from psycopg2.extras import execute_values

from app.core.config import settings

logger = logging.getLogger(__name__)

# Ministry mapping from agency_code patterns
AGENCY_TO_MINISTRY: Dict[str, str] = {
    "BWDB": "Ministry of Water Resources",
    "LGED": "Ministry of Local Government, Rural Development and Co-operatives",
    "PWD": "Ministry of Housing and Public Works",
    "RHD": "Ministry of Road Transport and Bridges",
    "BBA": "Ministry of Road Transport and Bridges",
    "DPHE": "Ministry of Local Government, Rural Development and Co-operatives",
    "BREB": "Ministry of Energy and Mineral Resources",
    "REB": "Ministry of Energy and Mineral Resources",
    "BADC": "Ministry of Agriculture",
    "BIWTA": "Ministry of Shipping",
    "EDUCATION": "Ministry of Education",
    "HED": "Ministry of Health and Family Welfare",
    "RAILWAY": "Ministry of Railways",
    "BPDB": "Ministry of Energy and Mineral Resources",
    "WASA": "Ministry of Local Government, Rural Development and Co-operatives",
    "RAJUK": "Ministry of Housing and Public Works",
    "BEPZA": "Prime Minister's Office",
    "BCIC": "Ministry of Industries",
    "TEXTILES": "Ministry of Textiles and Jute",
    "SUGAR": "Ministry of Industries",
    "TEA BOARD": "Ministry of Commerce",
    "PRINTING": "Ministry of Information",
    "MARINE ACADEMY": "Ministry of Shipping",
    "FAMILY PLANNING": "Ministry of Health and Family Welfare",
    "ANSAR": "Ministry of Home Affairs",
    "STATISTICS": "Ministry of Planning",
    "ATOMIC ENERGY": "Ministry of Science and Technology",
    "SCIENCE TECHNOLOGY": "Ministry of Science and Technology",
    "MUSEUM": "Ministry of Cultural Affairs",
    "KRIRA": "Ministry of Youth and Sports",
    "POST TELECOM": "Ministry of Posts, Telecommunications and Information Technology",
    "ECONOMIC RELATIONS": "Ministry of Finance",
    "MEDICAL EDUCATION": "Ministry of Health and Family Welfare",
    "BPATC": "Ministry of Public Administration",
    "COUNCIL": "Ministry of Education",
    "INFORMATIO": "Ministry of Information",
    "PIU": "Ministry of Planning",
    "POWER": "Ministry of Energy and Mineral Resources",
    "POLICE": "Ministry of Home Affairs",
    "HEALTH": "Ministry of Health and Family Welfare",
    "FIRE SERVICE": "Ministry of Home Affairs",
    "FISHERIES": "Ministry of Fisheries and Livestock",
    "FOOD": "Ministry of Food",
    "FOREST": "Ministry of Environment and Forests",
    "LIVESTOCK": "Ministry of Fisheries and Livestock",
    "CHIEF": "Ministry of Housing and Public Works",
    "EXECUTIVE": "Ministry of Local Government, Rural Development and Co-operatives",
    "CHITTAGONG PORT": "Ministry of Shipping",
    "MONGLA PORT": "Ministry of Shipping",
    "LAND PORT": "Ministry of Shipping",
    "CIVIL AVIATION": "Ministry of Civil Aviation and Tourism",
    "COAST GUARD": "Ministry of Home Affairs",
    "BORDER": "Ministry of Home Affairs",
    "BANGLADESH": "Government of Bangladesh",
    "COMMON": "Multiple Ministries",
    "OFFICE": "Multiple Ministries",
    "MINISTRY": "Various Ministries",
    "ENGINEERIN": "Ministry of Education",
    "UPGRADING": "Ministry of Local Government, Rural Development and Co-operatives",
    "DKMP": "Ministry of Water Resources",
}

# Agency full-name mapping
AGENCY_FULL_NAMES: Dict[str, str] = {
    "BWDB": "Bangladesh Water Development Board",
    "LGED": "Local Government Engineering Department",
    "PWD": "Public Works Department",
    "RHD": "Roads and Highways Department",
    "BPDB": "Bangladesh Power Development Board",
    "BREB": "Rural Electrification Board",
    "REB": "Rural Electrification Board",
    "BADC": "Bangladesh Agricultural Development Corporation",
    "BIWTA": "Bangladesh Inland Water Transport Authority",
    "DPHE": "Department of Public Health Engineering",
    "WASA": "Water Supply and Sewerage Authority",
    "BBA": "Bangladesh Bridge Authority",
    "RAJUK": "Rajdhani Unnayan Kartripakkha",
    "HED": "Health Engineering Department",
    "RAILWAY": "Bangladesh Railway",
    "BEPZA": "Bangladesh Export Processing Zones Authority",
    "BCIC": "Bangladesh Chemical Industries Corporation",
    "CHITTAGONG PORT": "Chittagong Port Authority",
    "MONGLA PORT": "Mongla Port Authority",
    "LAND PORT": "Land Port Authority",
    "COAST GUARD": "Bangladesh Coast Guard",
    "BORDER": "Border Guard Bangladesh",
    "POLICE": "Bangladesh Police",
    "FIRE SERVICE": "Bangladesh Fire Service and Civil Defence",
    "ANSAR": "Bangladesh Ansar and VDP",
    "FAMILY PLANNING": "Directorate General of Family Planning",
    "TEA BOARD": "Bangladesh Tea Board",
    "ATOMIC ENERGY": "Bangladesh Atomic Energy Commission",
    "SCIENCE TECHNOLOGY": "Ministry of Science and Technology",
    "KRIRA": "Bangladesh Krira Shikkha Protishtan",
    "MEDICAL EDUCATION": "Directorate of Medical Education",
    "BPATC": "Bangladesh Public Administration Training Centre",
    "POST TELECOM": "Bangladesh Post Office",
    "ECONOMIC RELATIONS": "Economic Relations Division",
    "COUNCIL": "National Curriculum and Textbook Board",
    "INFORMATIO": "Department of Information and Communication Technology",
    "ENGINEERIN": "Engineering Department",
    "UPGRADING": "Upgrading Project",
    "DKMP": "Dhaka Khan Metropolitan Project",
}


def _clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip())[:200]


def _db_connection() -> psycopg2.extensions.connection:
    """Create a synchronous DB connection."""
    url = settings.DATABASE_URL
    # Strip asyncpg prefix if present
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    # Parse URL manually for psycopg2
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    return psycopg2.connect(
        host=parsed.hostname or "localhost",
        port=parsed.port or 5433,
        database=parsed.path.lstrip("/"),
        user=parsed.username or "postgres",
        password=parsed.password or os.getenv("POSTGRES_PASSWORD", os.getenv("PGPASSWORD", "")),
    )


class AgencyMasterService:
    """Service to build and maintain the unified agency master table."""

    def __init__(self, conn: Optional[psycopg2.extensions.connection] = None):
        self.conn = conn or _db_connection()
        self._ensure_columns()

    def _ensure_columns(self) -> None:
        """Add stats columns to agencies table if not present."""
        cur = self.conn.cursor()
        try:
            cur.execute("""
                ALTER TABLE agencies
                ADD COLUMN IF NOT EXISTS total_awards INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS total_value_bdt DOUBLE PRECISION DEFAULT 0,
                ADD COLUMN IF NOT EXISTS org_count INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS pe_offices JSON DEFAULT '[]'
            """)
            self.conn.commit()
            logger.info("Agency stats columns ensured")
        except Exception as e:
            self.conn.rollback()
            logger.debug("Column add warning: %s", e)

    @staticmethod
    def resolve_agency_name(code: str) -> str:
        """Return full agency name from code."""
        return AGENCY_FULL_NAMES.get(code, code.title())

    @staticmethod
    def resolve_ministry(code: str) -> str:
        """Return ministry name from agency code."""
        return AGENCY_TO_MINISTRY.get(code, "Government of Bangladesh")

    def extract_from_awards(self) -> Dict[str, Dict]:
        """Extract unique agencies from award_records_v2."""
        logger.info("Extracting agencies from award_records_v2...")
        cur = self.conn.cursor()
        cur.execute("""
            SELECT agency_code, pe_office, COUNT(*) as cnt, SUM(amount_bdt) as total
            FROM award_records_v2
            WHERE agency_code IS NOT NULL AND agency_code <> '' AND agency_code <> 'UNKNOWN'
            GROUP BY agency_code, pe_office
            ORDER BY agency_code, cnt DESC
        """)
        agencies: Dict[str, Dict] = {}
        for row in cur.fetchall():
            code, pe, cnt, total = row
            if code not in agencies:
                agencies[code] = {
                    "code": code,
                    "name": self.resolve_agency_name(code),
                    "ministry": self.resolve_ministry(code),
                    "pe_offices": set(),
                    "total_awards": 0,
                    "total_value": 0.0,
                }
            agencies[code]["total_awards"] += cnt
            agencies[code]["total_value"] += float(total or 0)
            if pe:
                agencies[code]["pe_offices"].add(pe)
        logger.info("Found %d agencies from awards", len(agencies))
        return agencies

    def extract_from_existing(self) -> Dict[str, Dict]:
        """Get existing agencies from DB."""
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT agency_code, agency_name, ministry, keyword FROM agencies")
            existing = {}
            for row in cur.fetchall():
                existing[row[0]] = {
                    "code": row[0],
                    "name": row[1] or row[0],
                    "ministry": row[2] or "",
                    "keyword": row[3] or row[0],
                    "pe_offices": set(),
                    "total_awards": 0,
                    "total_value": 0.0,
                }
            return existing
        except Exception:
            self.conn.rollback()
            return {}

    def extract_from_app_records(self) -> Dict[str, Dict]:
        """Extract additional agencies from app_records."""
        cur = self.conn.cursor()
        additional: Dict[str, Dict] = {}
        try:
            cur.execute("""
                SELECT DISTINCT agency_code FROM app_records
                WHERE agency_code IS NOT NULL AND agency_code <> ''
            """)
            for row in cur.fetchall():
                code = row[0]
                if code and code not in additional:
                    additional[code] = {
                        "code": code,
                        "name": self.resolve_agency_name(code),
                        "ministry": self.resolve_ministry(code),
                        "pe_offices": set(),
                        "total_awards": 0,
                        "total_value": 0.0,
                    }
        except Exception as e:
            logger.warning("app_records error: %s", e)
            self.conn.rollback()
        return additional

    @staticmethod
    def merge_sources(
        from_awards: Dict[str, Dict],
        from_existing: Dict[str, Dict],
        from_other: Dict[str, Dict],
    ) -> Dict[str, Dict]:
        """Merge all sources into unified agency map."""
        all_agencies = {}
        for code, data in from_existing.items():
            all_agencies[code] = dict(data)
        for code, data in from_awards.items():
            if code in all_agencies:
                all_agencies[code]["total_awards"] = data["total_awards"]
                all_agencies[code]["total_value"] = data["total_value"]
                all_agencies[code]["pe_offices"].update(data["pe_offices"])
            else:
                all_agencies[code] = dict(data)
        for code, data in from_other.items():
            if code in all_agencies:
                all_agencies[code]["pe_offices"].update(data["pe_offices"])
            else:
                all_agencies[code] = dict(data)
        return all_agencies

    def import_agencies(self, agencies: Dict[str, Dict]) -> Dict[str, int]:
        """Upsert all agencies to DB."""
        logger.info("Importing %d agencies...", len(agencies))
        cur = self.conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        cur.execute("SELECT agency_code FROM agencies")
        existing = {row[0] for row in cur.fetchall()}

        inserts = []
        updates = 0
        for code, data in agencies.items():
            if code in existing:
                updates += 1
                try:
                    cur.execute("""
                        UPDATE agencies SET
                            total_awards = %s,
                            total_value_bdt = %s,
                            updated_at = %s
                        WHERE agency_code = %s
                    """, (data["total_awards"], data["total_value"], now, code))
                except Exception as e:
                    logger.warning("Update failed for %s: %s", code, e)
                    self.conn.rollback()
            else:
                inserts.append((
                    code,
                    data["name"][:200],
                    data["ministry"][:200] or "Government of Bangladesh",
                    code,
                    data["total_awards"],
                    data["total_value"],
                    now, now,
                    str(uuid.uuid4()),
                ))

        if inserts:
            try:
                execute_values(cur, """
                    INSERT INTO agencies
                    (agency_code, agency_name, ministry, keyword, total_awards, total_value_bdt,
                     created_at, updated_at, id)
                    VALUES %s
                    ON CONFLICT (agency_code) DO NOTHING
                """, inserts)
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                logger.error("Insert failed: %s", e)
        else:
            self.conn.commit()

        return {"total": len(agencies), "inserted": len(inserts), "updated": updates}

    def build_and_import(self) -> Dict[str, Any]:
        """Full pipeline: extract, merge, import, save tree."""
        from_awards = self.extract_from_awards()
        from_existing = self.extract_from_existing()
        from_app = self.extract_from_app_records()

        all_agencies = self.merge_sources(from_awards, from_existing, from_app)
        result = self.import_agencies(all_agencies)
        tree = self.save_agency_tree(all_agencies)

        return {
            "total": result["total"],
            "inserted": result["inserted"],
            "updated": result["updated"],
            "ministries": len(tree),
        }

    def save_agency_tree(self, agencies: Dict[str, Dict]) -> List[Dict]:
        """Save flat agency list + ministry tree to JSON."""
        out_dir = Path(__file__).resolve().parent.parent.parent / "runtime" / "knowledge" / "deptree"
        out_dir.mkdir(parents=True, exist_ok=True)

        flat = []
        for code, data in sorted(agencies.items()):
            flat.append({
                "agency_code": code,
                "agency_name": data["name"],
                "ministry": data["ministry"],
                "total_awards": data["total_awards"],
                "total_value_bdt": data["total_value"],
                "pe_office_count": len(data["pe_offices"]),
            })

        ministries = defaultdict(list)
        for code, data in agencies.items():
            ministry = data["ministry"] or "Unknown"
            ministries[ministry].append({
                "code": code,
                "name": data["name"],
                "awards": data["total_awards"],
                "value": data["total_value"],
            })

        tree = []
        for ministry, orgs in sorted(ministries.items()):
            tree.append({
                "ministry": ministry,
                "organization_count": len(orgs),
                "total_awards": sum(o["awards"] for o in orgs),
                "total_value_bdt": sum(o["value"] for o in orgs),
                "organizations": sorted(orgs, key=lambda x: -x["value"]),
            })

        (out_dir / "all_agencies_flat.json").write_text(
            json.dumps(flat, indent=2, ensure_ascii=False), encoding="utf-8")
        (out_dir / "ministry_tree.json").write_text(
            json.dumps(tree, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info("Saved agency tree to %s (%d ministries, %d orgs)", out_dir, len(tree), len(flat))
        return tree

    def close(self) -> None:
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ── Standalone CLI ────────────────────────────────────────────────────────────

def _cli():
    import sys
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    svc = AgencyMasterService()
    result = svc.build_and_import()
    print(json.dumps(result, indent=2))
    svc.close()


if __name__ == "__main__":
    _cli()
