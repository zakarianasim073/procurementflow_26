"""Normalization Layer (Phase 3 data pipeline).

Transforms raw crawler records (raw_crawl_data) into the canonical `pf_*`
domain tables with proper foreign-key resolution, upsert (INSERT ... ON
CONFLICT DO UPDATE) and version-bumping for change tracking.

Design
------
Raw Layer  (raw_crawl_data)
      │
      ▼
Normalizer  (this module)
      │  - resolve FK entities (PE, category, company)
      │  - upsert with version bump on change
      │  - emit change records to crawl_change_log
      ▼
Normalized Layer (pf_* tables)
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .connection import get_db_pool
from ..framework.logger import get_logger

log = get_logger("crawler.normalizer")

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_egp_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse e-GP date strings like '07-Jul-2026 14:00' into datetime."""
    if not value:
        return None
    m = re.search(r"(\d{1,2})[-/](\w{3,9})[-/](\d{2,4})\s*(\d{1,2}):(\d{2})", value.strip())
    if not m:
        return None
    day, mon, year, hh, mm = m.groups()
    mon_no = _MONTHS.get(mon[:3].lower())
    if not mon_no:
        return None
    year = int(year)
    if year < 100:
        year += 2000
    try:
        return datetime(year, mon_no, int(day), int(hh), int(mm))
    except ValueError:
        return None


def _hash(data: Dict[str, Any]) -> str:
    return hashlib.md5(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def _to_decimal(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    s = re.sub(r"[^\d.\-]", "", s)
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _diff_generic(prev: Dict[str, Any], norm: Dict[str, Any], keys: list) -> Dict[str, Any]:
    diff: Dict[str, Any] = {}
    for k in keys:
        old = prev.get(k)
        new = norm.get(k)
        if str(old) != str(new):
            diff[k] = {"from": str(old) if old is not None else None,
                       "to": str(new) if new is not None else None}
    return diff


def _diff_tender(prev: Dict[str, Any], norm: Dict[str, Any]) -> Dict[str, Any]:
    diff: Dict[str, Any] = {}
    keys = [
        "procuring_entity_id", "title", "status", "publish_date", "closing_date",
        "document_price", "category", "procurement_nature", "procurement_type",
        "procurement_method", "pe_office", "district", "agency_code", "source_url",
    ]
    for k in keys:
        old = prev.get(k)
        new = norm.get(k)
        if str(old) != str(new):
            diff[k] = {"from": str(old) if old is not None else None,
                       "to": str(new) if new is not None else None}
    return diff


class Normalizer:
    """Stateless service that upserts raw records into pf_* tables."""

    # ---- Procuring Entity ------------------------------------------------
    async def upsert_procuring_entity(
        self, name: str, agency_code: str = "", office: str = "",
        source: str = "egp",
    ) -> Optional[int]:
        if not name:
            return None
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO pf_procuring_entities (name, organization_id, office, agency_code, source, data_hash, updated_at)
                   VALUES ($1, NULL, $2, $3, $4, $5, NOW())
                   ON CONFLICT (name, organization_id) DO UPDATE
                     SET office=EXCLUDED.office, agency_code=EXCLUDED.agency_code,
                         updated_at=NOW(), version=pf_procuring_entities.version+1
                   RETURNING id""",
                name[:300], office[:200] or None, agency_code[:20] or None,
                source,
                # Include office in hash so version counter reflects real changes.
                _hash({"name": name, "agency_code": agency_code, "office": office}),
            )
            return row["id"] if row else None

    # ---- Category ---------------------------------------------------------
    async def upsert_category(self, name: str, code: str = "", source: str = "egp") -> Optional[int]:
        if not name:
            return None
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO pf_categories (name, code, source, data_hash, updated_at)
                   VALUES ($1, $2, $3, $4, NOW())
                   ON CONFLICT (code) DO UPDATE
                     SET name=EXCLUDED.name, updated_at=NOW(), version=pf_categories.version+1
                   RETURNING id""",
                name[:150], code[:50] or None, source,
                _hash({"name": name, "code": code}),
            )
            return row["id"] if row else None

    # ---- Company ----------------------------------------------------------
    async def upsert_company(
        self, name: str, registration_no: str = "", district: str = "",
        source: str = "egp",
    ) -> Optional[int]:
        if not name:
            return None
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Prefer match by registration_no when available, else by name
            existing = None
            if registration_no:
                existing = await conn.fetchrow(
                    "SELECT id FROM pf_companies WHERE registration_no=$1 AND NOT is_deleted",
                    registration_no[:100],
                )
            if not existing:
                existing = await conn.fetchrow(
                    "SELECT id FROM pf_companies WHERE name=$1 AND NOT is_deleted", name[:400]
                )
            if existing:
                return existing["id"]
            row = await conn.fetchrow(
                """INSERT INTO pf_companies (name, registration_no, district, source, data_hash, updated_at)
                   VALUES ($1, $2, $3, $4, $5, NOW()) RETURNING id""",
                name[:400], registration_no[:100] or None, district[:100] or None,
                source, _hash({"name": name, "registration_no": registration_no}),
            )
            return row["id"] if row else None

    # ---- Tender (core) ----------------------------------------------------
    async def upsert_tender(self, record: Dict[str, Any], source: str = "egp") -> Tuple[int, bool, Optional[dict]]:
        """Upsert a tender. Returns (id, is_new, changed_fields)."""
        tender_id = str(record.get("tender_id", "") or "")
        if not tender_id:
            return (0, False, None)

        package_no = (str(record.get("package_no", "") or "")[:400]) or None
        pe_id = await self.upsert_procuring_entity(
            record.get("procuring_entity") or record.get("pe_office") or "",
            agency_code=record.get("agency_code", ""),
            office=record.get("pe_office", ""),
        )
        publish_dt = parse_egp_datetime(record.get("publish_date"))
        closing_dt = parse_egp_datetime(record.get("closing_date"))

        norm = {
            "tender_id": tender_id,
            "package_no": package_no,
            "procuring_entity_id": pe_id,
            "title": record.get("title"),
            "status": record.get("status"),
            "publish_date": record.get("publish_date"),
            "closing_date": record.get("closing_date"),
            "document_price": _to_decimal(record.get("document_price")),
            "category": record.get("category"),
            "procurement_nature": record.get("procurement_nature"),
            "procurement_type": record.get("procurement_type"),
            "procurement_method": record.get("procurement_method"),
            "pe_office": record.get("pe_office"),
            "district": record.get("district"),
            "agency_code": record.get("agency_code"),
            "source_url": record.get("source_url"),
            "offline_id": str(record.get("offline_id") or "") or None,
        }
        details_json = record.get("details")
        if isinstance(details_json, dict):
            details_json = json.dumps(details_json, default=str)
        data_hash = _hash(norm)

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, data_hash, version FROM pf_tenders WHERE tender_id=$1 AND package_no IS NOT DISTINCT FROM $2",
                tender_id, package_no,
            )
            if existing and existing["data_hash"] == data_hash:
                # unchanged
                return (existing["id"], False, None)

            changed_fields = None
            if existing:
                prev = await conn.fetchrow(
                    "SELECT * FROM pf_tenders WHERE id=$1", existing["id"]
                )
                changed_fields = _diff_tender(prev, norm)

            row = await conn.fetchrow(
                """INSERT INTO pf_tenders
                   (tender_id, package_no, procuring_entity_id, title, status,
                    publish_date, closing_date, publish_datetime, closing_datetime,
                    document_price, category, procurement_nature, procurement_type,
                    procurement_method, pe_office, district, agency_code, source_url,
                    source, data_hash, offline_id, details, version, updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22::jsonb,1,NOW())
                   ON CONFLICT (tender_id, package_no) DO UPDATE
                     SET procuring_entity_id=EXCLUDED.procuring_entity_id,
                         title=EXCLUDED.title, status=EXCLUDED.status,
                         publish_date=EXCLUDED.publish_date, closing_date=EXCLUDED.closing_date,
                         publish_datetime=EXCLUDED.publish_datetime, closing_datetime=EXCLUDED.closing_datetime,
                         document_price=EXCLUDED.document_price, category=EXCLUDED.category,
                         procurement_nature=EXCLUDED.procurement_nature,
                         procurement_type=EXCLUDED.procurement_type,
                         procurement_method=EXCLUDED.procurement_method,
                         pe_office=EXCLUDED.pe_office, district=EXCLUDED.district,
                         agency_code=EXCLUDED.agency_code, source_url=EXCLUDED.source_url,
                         source=EXCLUDED.source, data_hash=EXCLUDED.data_hash,
                         offline_id=EXCLUDED.offline_id, details=EXCLUDED.details,
                         updated_at=NOW(), version=pf_tenders.version+1
                   RETURNING id""",
                tender_id, package_no, pe_id,
                str(norm["title"])[:4000] if norm["title"] else None,
                norm["status"][:50] if norm["status"] else None,
                norm["publish_date"][:50] if norm["publish_date"] else None,
                norm["closing_date"][:50] if norm["closing_date"] else None,
                publish_dt, closing_dt,
                norm["document_price"],
                norm["category"][:50] if norm["category"] else None,
                norm["procurement_nature"][:50] if norm["procurement_nature"] else None,
                norm["procurement_type"][:50] if norm["procurement_type"] else None,
                norm["procurement_method"][:50] if norm["procurement_method"] else None,
                    norm["pe_office"][:500] if norm["pe_office"] else None,
                    norm["district"][:300] if norm["district"] else None,
                norm["agency_code"][:20] if norm["agency_code"] else None,
                norm["source_url"],
                source, data_hash,
                norm["offline_id"],
                details_json,
            )
            new_id = row["id"] if row else (existing["id"] if existing else 0)
            is_new = existing is None
            if changed_fields:
                await conn.execute(
                    """INSERT INTO crawl_change_log
                       (table_name, record_id, change_type, previous_data, new_data, changed_fields)
                       VALUES ('pf_tenders', $1, 'updated', $2::jsonb, $3::jsonb, $4::jsonb)""",
                    str(new_id),
                    json.dumps({k: str(v) for k, v in (prev or {}).items()}, default=str),
                    json.dumps(norm, default=str),
                    json.dumps(changed_fields, default=str),
                )
            # ── Save relationships ──
            if pe_id:
                await self.save_relationship(
                    "tender", new_id, "procuring_entity", pe_id,
                    "procured_by", "fk_link",
                )
            return (new_id, is_new, changed_fields)

    # ---- Award -----------------------------------------------------------
    async def upsert_award(self, record: Dict[str, Any], source: str = "egp") -> Tuple[int, bool, Optional[dict]]:
        """Upsert an awarded-contract record. Returns (id, is_new, changed_fields)."""
        tender_id = str(record.get("tender_id", "") or "")
        package_no = (str(record.get("package_no", "") or "")[:400]) or None
        company_name = record.get("economic_operator_name") or record.get("contract_awarded_to") or ""
        reg_no = str(record.get("economic_operator_id") or record.get("company_unique_id") or "")
        district = str(record.get("district", "") or "")
        company_id = await self.upsert_company(company_name, reg_no, district) if company_name else None

        pe_name = record.get("pe_name") or record.get("pe_office") or ""
        pe_id = await self.upsert_procuring_entity(pe_name) if pe_name else None

        award_date = parse_egp_datetime(record.get("contract_signing_date") or record.get("noa_date"))
        value = _to_decimal(record.get("contract_value_bdt") or record.get("value_normalized_bdt") or record.get("value_raw"))

        norm = {
            "tender_id": tender_id,
            "package_no": package_no,
            "company_id": company_id,
            "procuring_entity_id": pe_id,
            "title": record.get("award_for") or record.get("title"),
            "award_date": record.get("contract_signing_date") or record.get("noa_date"),
            "contract_value": value,
            "status": record.get("status"),
            "offline_id": str(record.get("offline_id") or "") or None,
        }
        details_json = record.get("details")
        if isinstance(details_json, dict):
            details_json = json.dumps(details_json, default=str)
        data_hash = _hash({k: (str(v) if v is not None else None) for k, v in norm.items()})

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, data_hash, version FROM pf_awards WHERE tender_id IS NOT DISTINCT FROM $1 "
                "AND package_no IS NOT DISTINCT FROM $2 AND company_id IS NOT DISTINCT FROM $3",
                tender_id, package_no, company_id,
            )
            if existing and existing["data_hash"] == data_hash:
                return (existing["id"], False, None)

            changed_fields = None
            if existing:
                prev = await conn.fetchrow("SELECT * FROM pf_awards WHERE id=$1", existing["id"])
                changed_fields = _diff_generic(prev, norm, list(norm.keys()))

            if existing:
                # Hash changed: update the existing row by its PK.
                row = await conn.fetchrow(
                    """UPDATE pf_awards
                       SET tender_id=$1, package_no=$2, company_id=$3, procuring_entity_id=$4,
                           title=$5, award_date=$6, award_datetime=$7, contract_value=$8,
                           status=$9, source=$10, data_hash=$11, offline_id=$12,
                           details=$13::jsonb, updated_at=NOW(), version=pf_awards.version+1
                       WHERE id=$14 RETURNING id""",
                    tender_id, package_no, company_id, pe_id,
                    str(norm["title"])[:4000] if norm["title"] else None,
                    norm["award_date"][:50] if norm["award_date"] else None, award_date,
                    value, norm["status"][:50] if norm["status"] else None,
                    source, data_hash,
                    norm["offline_id"], details_json,
                    existing["id"],
                )
                new_id = row["id"] if row else existing["id"]
            else:
                row = await conn.fetchrow(
                    """INSERT INTO pf_awards
                       (award_id, tender_id, package_no, company_id, procuring_entity_id, title,
                        award_date, award_datetime, contract_value, status, source, data_hash,
                        offline_id, details, version, updated_at)
                       VALUES (NULL,$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,1,NOW())
                       RETURNING id""",
                    tender_id, package_no, company_id, pe_id,
                    str(norm["title"])[:4000] if norm["title"] else None,
                    norm["award_date"][:50] if norm["award_date"] else None, award_date,
                    value, norm["status"][:50] if norm["status"] else None,
                    source, data_hash,
                    norm["offline_id"], details_json,
                )
                new_id = row["id"] if row else 0
            if changed_fields:
                await conn.execute(
                    """INSERT INTO crawl_change_log
                       (table_name, record_id, change_type, previous_data, new_data, changed_fields)
                       VALUES ('pf_awards', $1, 'updated', $2::jsonb, $3::jsonb, $4::jsonb)""",
                    str(new_id),
                    json.dumps({k: str(v) for k, v in (prev or {}).items()}, default=str),
                    json.dumps(norm, default=str),
                    json.dumps(changed_fields, default=str),
                )
            # ── Save award relationships ──
            if company_id:
                await self.save_relationship("award", new_id, "company", company_id, "awarded_to", "fk_link")
            award_tender_id = None
            if tender_id:
                try:
                    trow = await conn.fetchrow("SELECT id FROM pf_tenders WHERE tender_id=$1 LIMIT 1", tender_id)
                    if trow:
                        award_tender_id = trow["id"]
                        await self.save_relationship("award", new_id, "tender", trow["id"], "belongs_to_tender", "string_match")
                except Exception:
                    pass
            if not award_tender_id and package_no:
                try:
                    trow = await conn.fetchrow("SELECT id FROM pf_tenders WHERE package_no=$1 LIMIT 1", package_no)
                    if trow:
                        await self.save_relationship("award", new_id, "tender", trow["id"], "belongs_to_tender", "package_match",
                                                     metadata={"package_no": package_no})
                except Exception:
                    pass
            if pe_id:
                await self.save_relationship("award", new_id, "procuring_entity", pe_id, "awarded_by", "fk_link")
            return (new_id, existing is None, changed_fields)

    # ---- Experience (eExperience) ----------------------------------------
    async def upsert_experience(self, record: Dict[str, Any], source: str = "egp") -> Tuple[int, bool, Optional[dict]]:
        company_name = record.get("contract_awarded_to") or ""
        reg_no = str(record.get("company_unique_id") or "")
        company_id = await self.upsert_company(company_name, reg_no) if company_name else None

        pe_name = record.get("pe_office") or record.get("organization") or ""
        pe_id = await self.upsert_procuring_entity(pe_name) if pe_name else None

        completion = parse_egp_datetime(
            record.get("contract_dates") or record.get("completion_date") or record.get("contract_end_date")
        )
        value = _to_decimal(
            record.get("contract_amount_bdt") or record.get("contract_value_bdt") or record.get("contract_value")
        )

        def _txt(*keys, default=None, maxlen=None):
            for k in keys:
                v = record.get(k)
                if v not in (None, ""):
                    s = str(v)
                    return s[:maxlen] if maxlen else s
            return default

        norm = {
            "company_id": company_id,
            "procuring_entity_id": pe_id,
            "project_name": _txt("name_of_work", "title"),
            "contract_value": value,
            "completion_date": _txt("contract_dates", "completion_date", "contract_end_date"),
            "completion_datetime": completion,
            "source": source,
            "tender_id": _txt("tender_id", maxlen=50),
            "tender_ref_no": _txt("tender_ref_no", maxlen=200),
            "package_no": _txt("package_no", maxlen=200),
            "package_name": _txt("package_name", maxlen=2000),
            "name_of_work": _txt("name_of_work", maxlen=4000),
            "contract_no": _txt("contract_no", maxlen=200),
            "contract_start_date": _txt("contract_start_date", maxlen=50),
            "contract_end_date": _txt("contract_end_date", maxlen=50),
            "work_completion_status": _txt("work_completion_status", maxlen=50),
            "procurement_nature": _txt("procurement_nature", maxlen=50),
            "procurement_method": _txt("procurement_method", maxlen=50),
            "work_category": _txt("work_category", maxlen=200),
            "tender_type": _txt("tender_type", maxlen=50),
            "physical_progress": _to_decimal(record.get("physical_progress")),
            "financial_progress": _to_decimal(record.get("financial_progress")),
            "experience_cert_no": _txt("experience_cert_no", maxlen=200),
            "pe_office_name": _txt("pe_office_name", maxlen=400),
            "organization_name": _txt("organization_name", maxlen=400),
            "pe_officer_name": _txt("pe_officer_name", maxlen=400),
            "ministry_division": _txt("ministry_division", maxlen=400),
            "company_name": _txt("company_name", "contract_awarded_to", maxlen=400),
            "is_jvca": _txt("is_jvca", maxlen=10),
            "remarks": _txt("remarks", maxlen=2000),
            "comments_by_pe": _txt("comments_by_pe", maxlen=2000),
            "date_physical_progress": _txt("date_physical_progress", maxlen=50),
            "date_financial_progress": _txt("date_financial_progress", maxlen=50),
            "tender_publication_date": _txt("tender_publication_date", maxlen=50),
        }
        details_json = json.dumps({k: v for k, v in record.items()}, default=str)
        data_hash = _hash({k: (str(v) if v is not None else None) for k, v in norm.items()})

        col_order = list(norm.keys())
        cols = ["experience_id"] + col_order + ["details", "version", "updated_at"]
        values_all = [norm[c] for c in col_order] + [details_json]
        insert_placeholders = ["NULL"] + [f"${i+1}" for i in range(len(col_order))] + [f"${len(col_order)+1}", "1", "NOW()"]
        insert_sql = (
            f"INSERT INTO pf_experience ({', '.join(cols)}) "
            f"VALUES ({', '.join(insert_placeholders)}) "
            "RETURNING id"
        )
        update_set_parts = [f"{c}=${i+1}" for i, c in enumerate(col_order)]
        update_set_parts.append(f"details=${len(col_order)+1}::jsonb")
        update_set_parts.append("updated_at=NOW()")
        update_set_parts.append("version=pf_experience.version+1")
        update_sql = (
            f"UPDATE pf_experience SET {', '.join(update_set_parts)} "
            f"WHERE id=${len(col_order)+2} RETURNING id"
        )

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, data_hash, version FROM pf_experience WHERE company_id IS NOT DISTINCT FROM $1 "
                "AND project_name IS NOT DISTINCT FROM $2",
                company_id, str(norm["project_name"])[:4000] if norm["project_name"] else None,
            )
            if existing and existing["data_hash"] == data_hash:
                return (existing["id"], False, None)

            changed_fields = None
            if existing:
                prev = await conn.fetchrow("SELECT * FROM pf_experience WHERE id=$1", existing["id"])
                changed_fields = _diff_generic(prev, norm, col_order)
                row = await conn.fetchrow(update_sql, *values_all, existing["id"])
            else:
                row = await conn.fetchrow(insert_sql, *values_all)
            new_id = row["id"] if row else (existing["id"] if existing else 0)
            if changed_fields:
                await conn.execute(
                    """INSERT INTO crawl_change_log
                       (table_name, record_id, change_type, previous_data, new_data, changed_fields)
                       VALUES ('pf_experience', $1, 'updated', $2::jsonb, $3::jsonb, $4::jsonb)""",
                    str(new_id),
                    json.dumps({k: str(v) for k, v in (prev or {}).items()}, default=str),
                    json.dumps(norm, default=str),
                    json.dumps(changed_fields, default=str),
                )
            if company_id:
                await self.save_relationship("experience", new_id, "company", company_id, "has_experience", "fk_link")
            if pe_id:
                await self.save_relationship("experience", new_id, "procuring_entity", pe_id, "experienced_at", "fk_link")
            return (new_id, existing is None, changed_fields)

    # ---- Debarment -------------------------------------------------------
    async def upsert_debarment(self, record: Dict[str, Any], source: str = "bppa") -> Tuple[int, bool, Optional[dict]]:
        company_name = record.get("firm_company") or ""
        company_id = await self.upsert_company(company_name) if company_name else None

        norm = {
            "company_id": company_id,
            "company_name": company_name,
            "authority": record.get("debarred_by"),
            "reason": record.get("reasons"),
            "start_date": record.get("debar_period"),
            "status": "active",
        }
        data_hash = _hash({k: (str(v) if v is not None else None) for k, v in norm.items()})

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, data_hash, version FROM pf_debarments WHERE company_id IS NOT DISTINCT FROM $1 "
                "AND company_name IS NOT DISTINCT FROM $2",
                company_id, company_name[:400] if company_name else None,
            )
            if existing and existing["data_hash"] == data_hash:
                return (existing["id"], False, None)

            changed_fields = None
            if existing:
                prev = await conn.fetchrow("SELECT * FROM pf_debarments WHERE id=$1", existing["id"])
                changed_fields = _diff_generic(prev, norm, list(norm.keys()))

            if existing:
                row = await conn.fetchrow(
                    """UPDATE pf_debarments
                       SET company_id=$1, company_name=$2, authority=$3, reason=$4,
                           start_date=$5, status=$6, source=$7, data_hash=$8,
                           updated_at=NOW(), version=pf_debarments.version+1
                       WHERE id=$9 RETURNING id""",
                    company_id, company_name[:400] if company_name else None,
                    norm["authority"][:200] if norm["authority"] else None,
                    norm["reason"],
                    norm["start_date"][:50] if norm["start_date"] else None,
                    norm["status"][:50],
                    source, data_hash, existing["id"],
                )
                new_id = row["id"] if row else existing["id"]
            else:
                row = await conn.fetchrow(
                    """INSERT INTO pf_debarments
                       (company_id, company_name, authority, reason, start_date, end_date, status,
                        source, data_hash, version, updated_at)
                       VALUES ($1,$2,$3,$4,$5,NULL,$6,$7,$8,1,NOW())
                       RETURNING id""",
                    company_id, company_name[:400] if company_name else None,
                    norm["authority"][:200] if norm["authority"] else None,
                    norm["reason"],
                    norm["start_date"][:50] if norm["start_date"] else None,
                    norm["status"][:50],
                    source, data_hash,
                )
                new_id = row["id"] if row else 0
            if changed_fields:
                await conn.execute(
                    """INSERT INTO crawl_change_log
                       (table_name, record_id, change_type, previous_data, new_data, changed_fields)
                       VALUES ('pf_debarments', $1, 'updated', $2::jsonb, $3::jsonb, $4::jsonb)""",
                    str(new_id),
                    json.dumps({k: str(v) for k, v in (prev or {}).items()}, default=str),
                    json.dumps(norm, default=str),
                    json.dumps(changed_fields, default=str),
                )
            if company_id:
                await self.save_relationship("debarment", new_id, "company", company_id, "has_debarment", "fk_link")
            return (new_id, existing is None, changed_fields)

    # ---- Document (normalized layer) ------------------------------------
    async def upsert_document(self, record: Dict[str, Any], source: str = "egp") -> Tuple[int, bool, Optional[dict]]:
        """Upsert a downloaded document metadata record into pf_documents."""
        tender_id = str(record.get("tender_id", "") or "")
        doc_type = str(record.get("doc_type", "OTHER") or "OTHER")
        filename = str(record.get("filename", "") or "")
        file_path = str(record.get("file_path", "") or "")
        if not (tender_id and doc_type and filename and file_path):
            return (0, False, None)

        norm = {
            "tender_id": tender_id,
            "doc_type": doc_type,
            "filename": filename,
            "file_path": file_path,
            "file_size": int(record.get("file_size", 0) or 0),
            "file_hash": record.get("file_hash"),
            "source_url": record.get("source_url"),
            "minio_path": record.get("minio_path"),
            "metadata": record.get("metadata"),
        }
        data_hash = _hash({k: (str(v) if v is not None else None) for k, v in norm.items()})

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id, data_hash, version FROM pf_documents WHERE tender_id=$1 "
                "AND doc_type=$2 AND filename=$3",
                tender_id, doc_type, filename,
            )
            if existing and existing["data_hash"] == data_hash:
                return (existing["id"], False, None)

            if existing:
                row = await conn.fetchrow(
                    """UPDATE pf_documents
                       SET file_path=$1, file_size=$2, file_hash=$3, source_url=$4,
                           minio_path=$5, metadata=$6::jsonb, source=$7, data_hash=$8,
                           updated_at=NOW(), version=pf_documents.version+1
                       WHERE id=$9 RETURNING id""",
                    file_path, norm["file_size"], norm["file_hash"], norm["source_url"],
                    norm["minio_path"],
                    json.dumps(norm["metadata"]) if norm["metadata"] else None,
                    source, data_hash, existing["id"],
                )
                new_id = row["id"] if row else existing["id"]
            else:
                row = await conn.fetchrow(
                    """INSERT INTO pf_documents
                       (tender_id, doc_type, filename, file_path, file_size, file_hash,
                        source_url, minio_path, metadata, source, data_hash, version, updated_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,$11,1,NOW())
                       RETURNING id""",
                    tender_id, doc_type, filename, file_path, norm["file_size"],
                    norm["file_hash"], norm["source_url"], norm["minio_path"],
                    json.dumps(norm["metadata"]) if norm["metadata"] else None,
                    source, data_hash,
                )
                new_id = row["id"] if row else 0
            if new_id and tender_id:
                try:
                    trow = await conn.fetchrow("SELECT id FROM pf_tenders WHERE tender_id=$1 LIMIT 1", tender_id)
                    if trow:
                        await self.save_relationship("document", new_id, "tender", trow["id"], "has_document", "string_match")
                except Exception:
                    pass
            return (new_id, existing is None, None)

    # ── Relationship Storage (Phase 4) ─────────────────────────────────────
    async def save_relationship(
        self,
        source_type: str, source_id: int,
        target_type: str, target_id: int,
        relationship_type: str,
        discovered_by: str = "fk_link",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store a typed, directed edge between two normalized entities."""
        if not source_id or not target_id:
            return False
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            try:
                await conn.execute(
                    """INSERT INTO pf_relationships
                       (source_type, source_id, target_type, target_id,
                        relationship_type, discovered_by, metadata, data_hash, updated_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8,NOW())
                       ON CONFLICT (source_type, source_id, target_type, target_id, relationship_type)
                       DO NOTHING""",
                    source_type, source_id, target_type, target_id,
                    relationship_type, discovered_by,
                    json.dumps(metadata) if metadata else None,
                    _hash({"s": source_type, "si": source_id, "t": target_type, "ti": target_id, "r": relationship_type}),
                )
                return True
            except Exception as exc:
                log.warning("save_relationship_failed", source=source_type, target=target_type, error=str(exc))
                return False


# Module-level singleton
_normalizer: Optional[Normalizer] = None


def get_normalizer() -> Normalizer:
    global _normalizer
    if _normalizer is None:
        _normalizer = Normalizer()
    return _normalizer