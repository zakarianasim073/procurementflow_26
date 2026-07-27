"""Deterministic pre-agent data quality guardrails for Works tenders."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import KnowledgeEntry


QUALITY_ENTRY_TYPE = "tender_data_quality"


def _issue(code: str, severity: str, message: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "evidence": evidence}


def _parse_date(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        from dateutil import parser

        parsed = parser.parse(str(value), dayfirst=True, fuzzy=True)
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except Exception:
        return None


def _deadline_values(value: Any, prefix: str = "") -> list[tuple[str, datetime]]:
    found: list[tuple[str, datetime]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if any(token in lowered for token in ("deadline", "closing", "submission_last")):
                parsed = _parse_date(child)
                if parsed:
                    found.append((path, parsed))
            if isinstance(child, (dict, list)):
                found.extend(_deadline_values(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_deadline_values(child, f"{prefix}[{index}]"))
    return found


def _document_checks(tender_id: str, supplied_paths: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    backend_root = Path(__file__).resolve().parents[2]
    upload_root = backend_root / "uploads" / tender_id
    paths = {Path(value).resolve() for value in supplied_paths.values() if value and Path(value).is_file()}
    if upload_root.is_dir():
        paths.update(path.resolve() for path in upload_root.rglob("*") if path.is_file())
    documents = [
        path for path in sorted(paths)
        if path.suffix.lower() in {".pdf", ".doc", ".docx", ".xls", ".xlsx"}
    ]
    issues: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    hashes: dict[str, list[str]] = {}
    for path in documents:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        hashes.setdefault(digest, []).append(str(path))
        record = {"name": path.name, "path": str(path), "size_bytes": len(raw), "sha256": digest}
        inventory.append(record)
        if path.suffix.lower() != ".pdf":
            continue
        if len(raw) < 512 or not raw.startswith(b"%PDF"):
            issues.append(_issue(
                "placeholder_pdf", "critical", f"{path.name} is not a usable PDF",
                {"path": str(path), "size_bytes": len(raw), "pdf_header": raw[:12].decode("latin-1", "replace")},
            ))
            continue
        try:
            from pypdf import PdfReader

            reader = PdfReader(path)
            if not reader.pages:
                issues.append(_issue("placeholder_pdf", "critical", f"{path.name} has no PDF pages", {"path": str(path)}))
            elif len(raw) < 2048:
                issues.append(_issue(
                    "placeholder_pdf", "warning", f"{path.name} is unusually small",
                    {"path": str(path), "size_bytes": len(raw), "pages": len(reader.pages)},
                ))
        except Exception as exc:
            issues.append(_issue(
                "invalid_pdf", "critical", f"{path.name} cannot be parsed",
                {"path": str(path), "error": str(exc)[:300]},
            ))
    for digest, duplicate_paths in hashes.items():
        if len(duplicate_paths) > 1:
            issues.append(_issue(
                "duplicate_documents", "warning", "Identical tender documents were detected",
                {"sha256": digest, "paths": duplicate_paths},
            ))
    return issues, inventory


async def evaluate_tender_data_quality(
    db: AsyncSession,
    *,
    tender_id: str,
    file_paths: dict[str, str] | None = None,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate and persist quality findings before downstream agents run."""
    file_paths = file_paths or {}
    issues, inventory = _document_checks(tender_id, file_paths)
    live = (
        await db.execute(text("""
            SELECT tender_id, package_no, closing_datetime, publish_datetime
            FROM pf_tenders
            WHERE tender_id = :tid OR package_no = :tid
            ORDER BY updated_at DESC LIMIT 1
        """), {"tid": tender_id})
    ).mappings().first()
    package_no = str(live["package_no"] or "") if live else ""
    app = None
    if package_no:
        app = (
            await db.execute(text("""
                SELECT id, package_no, normalized_package_no, estimated_cost_bdt,
                       deadline, updated_at
                FROM app_records
                WHERE normalized_package_no =
                    regexp_replace(regexp_replace(upper(:package_no), '\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g')
                  AND lower(coalesce(category, 'works')) = 'works'
                ORDER BY updated_at DESC NULLS LAST LIMIT 1
            """), {"package_no": package_no})
        ).mappings().first()

    amount = float(app["estimated_cost_bdt"] or 0) if app else 0.0
    if amount > 0 and amount < 10:
        amount *= 10_000_000
    if not app:
        issues.append(_issue("missing_app_match", "warning", "No normalized APP package match was found", {"package_no": package_no}))
    elif amount < 100_000 or amount > 1_000_000_000_000:
        issues.append(_issue(
            "implausible_currency", "critical", "APP estimate is outside plausible Works procurement bounds",
            {"app_record_id": app["id"], "amount_bdt": amount, "package_no": package_no},
        ))
    if app and app["updated_at"]:
        updated = app["updated_at"]
        updated = updated.replace(tzinfo=timezone.utc) if updated.tzinfo is None else updated
        age_days = (datetime.now(timezone.utc) - updated).days
        if age_days > 730:
            issues.append(_issue(
                "stale_app_match", "warning", "Matched APP record is more than two years old",
                {"app_record_id": app["id"], "updated_at": updated.isoformat(), "age_days": age_days},
            ))

    knowledge = (
        await db.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.tender_id == tender_id,
                KnowledgeEntry.entry_type == "tender_document",
                KnowledgeEntry.is_archived.is_(False),
            )
            .order_by(KnowledgeEntry.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    deadlines: list[tuple[str, datetime]] = []
    if live and live["closing_datetime"]:
        deadlines.append(("pf_tenders.closing_datetime", live["closing_datetime"]))
    if app and app["deadline"]:
        parsed_app_deadline = _parse_date(app["deadline"])
        if parsed_app_deadline:
            deadlines.append(("app_records.deadline", parsed_app_deadline))
    if knowledge:
        deadlines.extend(_deadline_values(knowledge.data or {}, "tender_document"))
    normalized_deadlines = [
        (source, value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value)
        for source, value in deadlines
    ]
    if normalized_deadlines:
        earliest = min(value for _, value in normalized_deadlines)
        latest = max(value for _, value in normalized_deadlines)
        if (latest - earliest).total_seconds() > 24 * 3600:
            issues.append(_issue(
                "conflicting_deadlines", "critical", "Tender deadline sources differ by more than 24 hours",
                {"sources": [{"source": source, "value": value.isoformat()} for source, value in normalized_deadlines]},
            ))

    critical = sum(1 for issue in issues if issue["severity"] == "critical")
    warnings = sum(1 for issue in issues if issue["severity"] == "warning")
    score = max(0, 100 - critical * 30 - warnings * 8)
    status = "blocked" if critical else "warning" if warnings else "passed"
    now = datetime.now(timezone.utc)
    payload = {
        "status": status,
        "score": score,
        "agent_use_allowed": critical == 0,
        "critical_count": critical,
        "warning_count": warnings,
        "issues": issues,
        "document_inventory": inventory,
        "app_match": {
            "record_id": app["id"] if app else None,
            "package_no": package_no,
            "estimated_cost_bdt": amount,
            "updated_at": app["updated_at"].isoformat() if app and app["updated_at"] else None,
        },
        "checked_at": now.isoformat(),
    }
    checksum = hashlib.sha256(f"{tender_id}:{payload}".encode()).hexdigest()
    entry = (
        await db.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.tender_id == tender_id,
                KnowledgeEntry.entry_type == QUALITY_ENTRY_TYPE,
                KnowledgeEntry.is_archived.is_(False),
            )
            .order_by(KnowledgeEntry.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if entry is None:
        entry = KnowledgeEntry(
            id=str(uuid.uuid4()),
            entry_type=QUALITY_ENTRY_TYPE,
            tender_id=tender_id,
            tenant_id=tenant_id,
            title=f"Data quality guardrails for {tender_id}",
            source="pre_agent_quality_gate",
            procurement_type="Works",
            tags={"works_only": True, "pre_agent_gate": True},
            data=payload,
            checksum=checksum,
        )
        db.add(entry)
    else:
        entry.data = payload
        entry.checksum = checksum
    entry.summary = f"Quality {status}: {critical} critical, {warnings} warnings"
    await db.commit()
    return payload
