"""W-009 — zero envelope-less outputs (test-enforced) + evidence persisted via API.

Covers all three W-E3 engines: qualification (W-006), PPR-2025 (W-007), BOQ (W-008),
and proves evidence hits POST /v1/knowledge/evidence through the typed client.
"""

from __future__ import annotations

import httpx
import pytest

from app.agents.core.base import AgentStatus
from app.agents.core.envelope import build_envelope, is_enveloped
from app.agents.evaluation.eligibility_compliance import EligibilityComplianceAgent
from app.agents.evaluation.ppr2025_compliance import PPR2025ComplianceAgent
from app.clients.epdp import EPDPClient, EPDPClientConfig
from app.services.boq_processor import BOQProcessor

QUALIFICATION_CONTEXT = {
    "company_profile": {
        "company_name": "Test Ltd", "years_experience": 10, "avg_turnover": 60_000_000,
        "equipment": ["excavator"], "engineers_count": 6, "licenses": ["trade"],
        "similar_works": [{"title": "A", "value_bdt": 30_000_000}],
    },
    "upstream": {
        "agent-004-document-ai": {"experience_required": "5 years", "turnover_required": 1},
        "agent-006-spec-intelligence": {"required_equipment": ["excavator"]},
    },
}

PPR_CONTEXT = {
    "tender_id": "T-1",
    "tender_info": {"tender_type": "works"},
    "vendor_profile": {"name": "Test Ltd"},
    "submitted_docs": {"bid_security": True},
    "upstream": {"agent-007-eligibility-compliance": {}},
}


def _evidence_capture():
    posted = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/knowledge/evidence":
            import json
            posted.append(json.loads(request.content))
            return httpx.Response(201, json={"stored": True, "tenant_id": "t1", "evidence": {}})
        return httpx.Response(404)

    client = EPDPClient(
        EPDPClientConfig(base_url="http://epdp.test", api_key="k", tenant_id="t1"),
        transport=httpx.MockTransport(handler),
    )
    return client, posted


# ── envelope shape ────────────────────────────────────────────────────

def test_build_envelope_rejects_malformed():
    with pytest.raises(ValueError):
        build_envelope(1, "CERTAIN", [], "v1")
    with pytest.raises(ValueError):
        build_envelope(1, "HIGH", [], "")


@pytest.mark.asyncio
async def test_qualification_output_is_enveloped():
    result = await EligibilityComplianceAgent().execute(dict(QUALIFICATION_CONTEXT))
    assert result.status == AgentStatus.SUCCESS
    assert is_enveloped(result.output)
    assert result.output["envelope"]["confidence"] == "HIGH"
    assert result.output["envelope"]["evidence"]


@pytest.mark.asyncio
async def test_ppr_output_is_enveloped():
    agent = PPR2025ComplianceAgent()
    async def _noop(**kwargs):
        return None
    agent.share_knowledge = _noop
    result = await agent.execute(dict(PPR_CONTEXT))
    assert is_enveloped(result.output)
    assert result.output["envelope"]["rule_version"] == result.output["ruleset_version"]
    assert result.output["envelope"]["knowledge_refs"], "findings' clauses must flow into refs"


@pytest.mark.asyncio
async def test_boq_compare_output_is_enveloped(monkeypatch, tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Item No", "Code", "Description", "Unit", "Qty", "Rate", "Amount"])
    ws.append(["1", "04-180-00", "Earthwork", "cum", 10.0, 100.0, 2000.0])  # seeded error
    path = tmp_path / "boq.xlsx"
    wb.save(path)

    proc = BOQProcessor()
    monkeypatch.setattr(proc, "_compare_with_sor", lambda *a, **k: [])
    monkeypatch.setattr(proc, "_generate_excel", lambda *a, **k: {})
    result = await proc.compare(str(path))

    assert is_enveloped(result)
    assert result["arithmetic_error_count"] == 1
    assert any("stated 2000.0" in e for e in result["envelope"]["evidence"])


# ── evidence persisted BEFORE surfacing (L5) ──────────────────────────

@pytest.mark.asyncio
async def test_agents_persist_evidence_via_api():
    client, posted = _evidence_capture()
    async with client:
        context = {**QUALIFICATION_CONTEXT, "evidence_client": client}
        await EligibilityComplianceAgent().execute(context)

        ppr = PPR2025ComplianceAgent()
        async def _noop(**kwargs):
            return None
        ppr.share_knowledge = _noop
        await ppr.execute({**PPR_CONTEXT, "evidence_client": client})

    assert len(posted) == 2
    for item in posted:
        assert item["claim"]
        assert item["source_type"] == "agent_finding"
        assert "@" in item["source_reference"], "must cite agent id + version"


@pytest.mark.asyncio
async def test_missing_evidence_client_does_not_block_but_envelope_remains():
    result = await EligibilityComplianceAgent().execute(dict(QUALIFICATION_CONTEXT))
    assert is_enveloped(result.output)
