"""W-003 wiring (ProcureFlow side) — client call shape + beat registration + profile mapping."""

from __future__ import annotations

import httpx
import json
import pytest

from app.clients.epdp import EPDPClient, EPDPClientConfig
from app.workers.tasks.shortlist_tasks import _load_profiles

RESULT = [
    {
        "firm_id": "pilot-firm-01",
        "generated_at": "2026-07-11T06:00:00Z",
        "total_considered": 12,
        "entries": [{"egp_reference": "EGP-1", "match_reasons": ["agency: LGED"]}],
    }
]


@pytest.mark.asyncio
async def test_client_shortlist_posts_profiles_and_parses_result():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.url.path == "/v1/tender/shortlist"
        body = json.loads(request.content)
        assert body["profiles"][0]["firm_id"] == "pilot-firm-01"
        assert "opportunities" not in body  # store-backed by default
        return httpx.Response(200, json=RESULT)

    config = EPDPClientConfig(base_url="http://epdp.test", api_key="k", tenant_id="t")
    async with EPDPClient(config, transport=httpx.MockTransport(handler)) as client:
        results = await client.shortlist([{"firm_id": "pilot-firm-01"}])

    assert len(seen) == 1
    assert results[0].firm_id == "pilot-firm-01"
    assert results[0].total_considered == 12
    assert len(results[0].entries) == 1


def test_pilot_profiles_map_to_epdp_shape():
    profiles = _load_profiles()
    assert len(profiles) == 5
    for p in profiles:
        assert set(p) == {"firm_id", "preferred_agencies", "districts", "categories", "avg_turnover"}
        assert p["categories"] == ["Works"]
        assert p["avg_turnover"] > 0


def test_beat_schedule_registers_daily_shortlist():
    from app.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["epdp-shortlist-daily"]
    assert entry["task"] == "epdp_daily_shortlist"
    assert "app.workers.tasks.shortlist_tasks" in celery_app.conf.include


def test_task_routed_to_low_queue():
    from app.workers.tasks.shortlist_tasks import epdp_daily_shortlist

    assert epdp_daily_shortlist.queue == "low"
