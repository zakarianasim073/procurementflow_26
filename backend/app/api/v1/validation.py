"""Validation API routes for tender/BOQ compliance checks."""

import json
from uuid import uuid4
from typing import Any, Dict, List
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_optional_user
from app.db.base import get_async_session
from app.schemas.response_models import (
    ValidationFinding,
    ComplianceCheck,
    ComplianceRule,
)

router = APIRouter(prefix="/validation", tags=["validation"])


class ValidationItem(BaseModel):
    item_no: str = ""
    description: str = ""
    unit: str = ""
    quantity: float = 0.0
    rate: float | None = None


class ValidationRequest(BaseModel):
    tender_id: str = ""
    items: List[ValidationItem] = Field(default_factory=list)
    required_documents: List[str] = Field(default_factory=list)
    provided_documents: List[str] = Field(default_factory=list)


def _validate_items(items: List[ValidationItem]) -> List[Dict[str, Any]]:
    findings = []
    seen = set()
    for item in items:
        key = (item.item_no or "").strip()
        if key and key in seen:
            findings.append({"severity": "error", "code": "duplicate_item", "item_no": key})
        seen.add(key)
        if item.quantity <= 0:
            findings.append({"severity": "error", "code": "non_positive_quantity", "item_no": key})
        if not item.description.strip():
            findings.append({"severity": "error", "code": "missing_description", "item_no": key})
        if not item.unit.strip():
            findings.append({"severity": "warning", "code": "missing_unit", "item_no": key})
        if item.rate is None:
            findings.append({"severity": "warning", "code": "missing_rate", "item_no": key})
    return findings


def _score_findings(findings: List[Dict[str, Any]]) -> float:
    if not findings:
        return 100.0
    errors = sum(1 for item in findings if item.get("severity") == "error")
    warnings = sum(1 for item in findings if item.get("severity") == "warning")
    return max(0.0, 100.0 - errors * 25.0 - warnings * 5.0)


async def _persist_compliance_check(
    db: AsyncSession,
    *,
    tender_id: str,
    check_name: str,
    check_type: str,
    findings: List[Dict[str, Any]],
    source: str,
) -> bool:
    if not tender_id:
        return False
    score = _score_findings(findings)
    passed = not any(item.get("severity") == "error" for item in findings)
    recommendation = "Ready" if passed else "Fix blocking validation errors before submission"
    await db.execute(text("""
        INSERT INTO compliance_checks (
            id, agent_result_id, tender_id, check_name, check_type,
            passed, score, max_score, details, recommendation, created_at
        )
        VALUES (
            :id, NULL, :tender_id, :check_name, :check_type,
            :passed, :score, 100, :details, :recommendation, now()
        )
    """), {
        "id": str(uuid4()),
        "tender_id": tender_id,
        "check_name": check_name,
        "check_type": check_type,
        "passed": passed,
        "score": score,
        "details": json.dumps({"source": source, "findings": findings}, default=str),
        "recommendation": recommendation,
    })
    await db.commit()
    return True


@router.post("/check", response_model=ComplianceCheck)
async def validate_payload(
    req: ValidationRequest,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    findings = _validate_items(req.items)
    missing_docs = sorted(set(req.required_documents) - set(req.provided_documents))
    findings.extend({"severity": "error", "code": "missing_document", "document": doc} for doc in missing_docs)
    
    score = _score_findings(findings)
    passed = not any(f["severity"] == "error" for f in findings)
    overall_status = "compliant" if passed else "non_compliant"
    if findings and not passed:
        overall_status = "non_compliant"
    elif findings:
        overall_status = "partial"
    
    # Build rules from findings
    rules = []
    for i, finding in enumerate(findings):
        rules.append(ComplianceRule(
            rule_id=f"rule_{i}",
            rule_code=finding.get("code", "unknown"),
            title=finding.get("code", "Validation Check").replace("_", " ").title(),
            description=finding.get("message", f"Validation check: {finding.get('code', 'unknown')}"),
            category="validation",
            status="fail" if finding.get("severity") == "error" else "warning" if finding.get("severity") == "warning" else "pass",
            details=f"Item: {finding.get('item_no', 'N/A')}, Document: {finding.get('document', 'N/A')}",
        ))
    
    check = ComplianceCheck(
        check_id=str(uuid4()),
        tender_id=req.tender_id,
        rules=rules,
        overall_status=overall_status,
        score=score,
        checked_at=datetime.utcnow().isoformat() + "Z",
    )
    
    persisted = False
    try:
        persisted = await _persist_compliance_check(
            db,
            tender_id=req.tender_id,
            check_name="payload_rule_engine",
            check_type="payload",
            findings=findings,
            source="rule_engine",
        )
    except Exception:
        await db.rollback()
    
    return check


@router.get("/tender/{tender_id}", response_model=ComplianceCheck)
async def validate_tender(
    tender_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_optional_user),
):
    rows = await db.execute(text("""
        SELECT item_no, description, unit, quantity, quoted_rate AS rate
        FROM boq_items
        WHERE tender_id = :tender_id
        ORDER BY item_no
        LIMIT 1000
    """), {"tender_id": tender_id})
    items = [ValidationItem(**dict(row)) for row in rows.mappings()]
    findings = _validate_items(items)
    if not items:
        findings = [{"severity": "warning", "code": "no_boq_items", "message": "No BOQ items persisted for this tender"}]
    
    score = _score_findings(findings)
    passed = not any(f["severity"] == "error" for f in findings)
    overall_status = "compliant" if passed else "non_compliant"
    if findings and not passed:
        overall_status = "non_compliant"
    elif findings:
        overall_status = "partial"
    
    rules = []
    for i, finding in enumerate(findings):
        rules.append(ComplianceRule(
            rule_id=f"rule_{i}",
            rule_code=finding.get("code", "unknown"),
            title=finding.get("code", "Validation Check").replace("_", " ").title(),
            description=finding.get("message", f"Validation check: {finding.get('code', 'unknown')}"),
            category="validation",
            status="fail" if finding.get("severity") == "error" else "warning" if finding.get("severity") == "warning" else "pass",
            details=f"Item: {finding.get('item_no', 'N/A')}",
        ))
    
    check = ComplianceCheck(
        check_id=str(uuid4()),
        tender_id=tender_id,
        rules=rules,
        overall_status=overall_status,
        score=score,
        checked_at=datetime.utcnow().isoformat() + "Z",
    )
    
    persisted = False
    try:
        persisted = await _persist_compliance_check(
            db,
            tender_id=tender_id,
            check_name="boq_item_validation",
            check_type="boq_items",
            findings=findings,
            source="boq_items",
        )
    except Exception:
        await db.rollback()
    
    return check
