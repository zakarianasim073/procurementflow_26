"""X-005 acceptance: every recommendation's envelope references PERSISTED evidence —
zero refs to nonexistent evidence rows."""

from __future__ import annotations

import json
import uuid

import httpx
import pytest

from app.agents.evaluation.eligibility_compliance import EligibilityComplianceAgent
from app.agents.evaluation.ppr2025_compliance import PPR2025ComplianceAgent
from app.clients.epdp import EPDPClient, EPDPClientConfig
from tests.test_envelope_w009 import PPR_CONTEXT, QUALIFICATION_CONTEXT


def _evidence_server():
    """Mock P03: stores evidence, returns real ids — the source of truth."""
    stored_ids: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/knowledge/evidence"
        body = json.loads(request.content)
        eid = str(uuid.uuid4())
        stored_ids.append(eid)
        return httpx.Response(201, json={"stored": True, "tenant_id": "t1",
                                         "evidence": {"id": eid, **body}})

    client = EPDPClient(
        EPDPClientConfig(base_url="http://epdp.test", api_key="k", tenant_id="t1"),
        transport=httpx.MockTransport(handler),
    )
    return client, stored_ids


@pytest.mark.asyncio
async def test_qualification_envelope_refs_persisted_evidence():
    client, stored = _evidence_server()
    async with client:
        result = await EligibilityComplianceAgent().execute(
            {**QUALIFICATION_CONTEXT, "evidence_client": client, "workspace_id": "ws-9"}
        )
    refs = result.output["envelope"]["knowledge_refs"]
    assert refs, "recommendation must reference evidence"
    for ref in refs:
        assert ref.startswith("evidence:")
        assert ref.split(":", 1)[1] in stored, f"ref to nonexistent evidence: {ref}"


@pytest.mark.asyncio
async def test_ppr_envelope_refs_persisted_evidence_plus_clauses():
    client, stored = _evidence_server()
    ppr = PPR2025ComplianceAgent()

    async def _noop(**kwargs):
        return None
    ppr.share_knowledge = _noop

    async with client:
        result = await ppr.execute({**PPR_CONTEXT, "evidence_client": client})

    refs = result.output["envelope"]["knowledge_refs"]
    evidence_refs = [r for r in refs if r.startswith("evidence:")]
    assert len(evidence_refs) == 1
    assert evidence_refs[0].split(":", 1)[1] in stored
    assert any("PPR-2025" in r for r in refs), "clause refs preserved alongside evidence ref"


@pytest.mark.asyncio
async def test_unwired_run_has_no_dangling_refs():
    """Offline (no evidence client): envelope must carry ZERO evidence refs —
    never a ref that was not persisted."""
    result = await EligibilityComplianceAgent().execute(dict(QUALIFICATION_CONTEXT))
    refs = result.output["envelope"]["knowledge_refs"]
    assert not [r for r in refs if r.startswith("evidence:")]
