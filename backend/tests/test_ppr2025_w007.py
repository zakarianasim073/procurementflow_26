"""W-007 — PPR-2025 Compliance Flags: every flag cites clause + ruleset version.

Deterministic rule checks (no ML, no legal-advice text) plus the Validation
Dataset harness (skips until backend/tests/data/validation_dataset/ppr/ lands).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.core.base import AgentStatus
from app.agents.evaluation.ppr2025_compliance import (
    RULESET_VERSION,
    PPR2025ComplianceAgent,
)

DATASET = Path(__file__).parent / "data" / "validation_dataset" / "ppr"

WORKS_CONTEXT = {
    "tender_id": "T-TEST-01",
    "tender_info": {"tender_type": "works"},
    "vendor_profile": {"name": "Test Constructions Ltd"},
    "submitted_docs": {
        "bid_security": True,
        "trade_license": True,
        # income_tax_certificate deliberately missing -> critical flag expected
    },
    "upstream": {"agent-007-eligibility-compliance": {}},
}


async def _run(context: dict) -> dict:
    agent = PPR2025ComplianceAgent()
    # Brain knowledge-sharing is out of scope here (W-009 wires evidence).
    if hasattr(agent, "share_knowledge"):
        async def _noop(**kwargs):
            return None
        agent.share_knowledge = _noop
    result = await agent.execute(context)
    assert result.status == AgentStatus.SUCCESS
    return result.output


@pytest.mark.asyncio
async def test_every_finding_cites_clause_and_version():
    output = await _run(WORKS_CONTEXT)

    assert output["ruleset_version"] == RULESET_VERSION
    assert output["findings"], "expected findings for an incomplete submission"
    for finding in output["findings"]:
        assert finding["clause"], f"finding without clause: {finding['check_name']}"
        assert finding["ruleset_version"] == RULESET_VERSION
    for flag in output["critical_failures"] + output["warnings"]:
        assert flag["clause"], f"flag without clause: {flag}"


@pytest.mark.asyncio
async def test_missing_critical_document_is_flagged():
    output = await _run(WORKS_CONTEXT)
    failed_names = {f["check"] for f in output["critical_failures"]}
    assert any("income_tax" in name or "Income Tax" in name for name in failed_names) or (
        output["document_checks"]["passed"] is False
    )


@pytest.mark.asyncio
async def test_ruleset_version_overridable_per_tenant():
    context = {**WORKS_CONTEXT, "ruleset_version": "PPR-2025/PPA-amendment r2-tenant9"}
    output = await _run(context)
    assert output["ruleset_version"] == "PPR-2025/PPA-amendment r2-tenant9"
    assert all(f["ruleset_version"] == "PPR-2025/PPA-amendment r2-tenant9" for f in output["findings"])


@pytest.mark.asyncio
async def test_schedule_findings_cite_their_schedule():
    output = await _run(WORKS_CONTEXT)
    schedule_findings = [f for f in output["findings"] if f["type"] == "schedule"]
    for f in schedule_findings:
        assert "Schedule" in f["clause"]


@pytest.mark.asyncio
async def test_validation_dataset_rule_correctness():
    """W-007 acceptance: >=95% rule correctness on the validation set."""
    cases = sorted(DATASET.glob("*.json")) if DATASET.exists() else []
    cases = [c for c in cases if json.loads(c.read_text(encoding="utf-8")).get("expected_passed") is not None]
    if not cases:
        pytest.skip("PPR validation dataset not labeled yet")

    correct = 0
    disagreements = []
    for case_file in cases:
        case = json.loads(case_file.read_text(encoding="utf-8"))
        output = await _run(case["context"])
        if output["overall_passed"] == case["expected_passed"]:
            correct += 1
        else:
            disagreements.append(
                f"{case_file.name}: engine={output['overall_passed']} manual={case['expected_passed']} "
                f"[{case.get('manual_clause', '')}] {case.get('manual_reason', '')}"
            )

    print(f"\nW-007 rule correctness={correct / len(cases):.1%} ({correct}/{len(cases)})")
    for d in disagreements:
        print("  DISAGREE", d)
    assert correct / len(cases) >= 0.95
