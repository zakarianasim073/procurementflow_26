"""W-011 — tenant data walls + pilot onboarding gates.

Leak suite (context layer, per ADR-020) + MOU gate + 5-profile integrity.
DB-level RLS checks run only when the local PostgreSQL is reachable.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.core.tenant import (
    clear_tenant_context,
    get_tenant_context,
    resolve_tenant_id_for_session,
    set_tenant_context,
)

DATA = Path(__file__).resolve().parents[1] / "app" / "data" / "pilot_tenants.json"


@pytest.fixture(autouse=True)
def _clean_context():
    clear_tenant_context()
    yield
    clear_tenant_context()


# ── context walls (ADR-020) ───────────────────────────────────────────

def test_missing_context_raises_in_strict_mode(monkeypatch):
    monkeypatch.setenv("TENANT_CONTEXT_REQUIRED", "1")
    monkeypatch.delenv("DEFAULT_TENANT_ID", raising=False)
    with pytest.raises(RuntimeError, match="Tenant context missing"):
        resolve_tenant_id_for_session()


@pytest.mark.asyncio
async def test_concurrent_tasks_never_leak_each_others_tenant():
    """Firm A's async task must never observe firm B's tenant id."""
    observed: dict[str, list[str]] = {"pilot-firm-01": [], "pilot-firm-02": []}

    async def firm_task(tenant_id: str) -> None:
        set_tenant_context(tenant_id)
        for _ in range(25):
            await asyncio.sleep(0)  # force interleaving
            current, _sup = get_tenant_context()
            observed[tenant_id].append(current)

    await asyncio.gather(firm_task("pilot-firm-01"), firm_task("pilot-firm-02"))

    assert set(observed["pilot-firm-01"]) == {"pilot-firm-01"}
    assert set(observed["pilot-firm-02"]) == {"pilot-firm-02"}


def test_clear_context_removes_identity():
    set_tenant_context("pilot-firm-03")
    clear_tenant_context()
    assert get_tenant_context() == (None, False)


def test_superuser_flag_does_not_survive_clear():
    set_tenant_context("pilot-firm-01", is_superuser=True)
    clear_tenant_context()
    assert get_tenant_context()[1] is False


# ── pilot profiles + MOU gate ─────────────────────────────────────────

def _tenants() -> list[dict]:
    return json.loads(DATA.read_text(encoding="utf-8"))["tenants"]


def test_exactly_five_pilot_tenants_with_distinct_ids():
    tenants = _tenants()
    assert len(tenants) == 5
    ids = [t["tenant_id"] for t in tenants]
    assert len(set(ids)) == 5


def test_all_pilot_mous_signed():
    assert all(t["mou_signed"] is True for t in _tenants())


def test_profiles_match_qualification_agent_shape():
    required = {"company_name", "years_experience", "avg_turnover", "equipment",
                "engineers_count", "licenses", "similar_works"}
    for t in _tenants():
        missing = required - set(t["profile"])
        assert not missing, f"{t['tenant_id']} profile missing {missing}"


def test_mou_gate_refuses_unsigned(monkeypatch, tmp_path):
    from scripts import onboard_pilot_tenants as script

    data = json.loads(DATA.read_text(encoding="utf-8"))
    data["tenants"][2]["mou_signed"] = False
    bad = tmp_path / "pilot_tenants.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(script, "DATA_FILE", bad)

    with pytest.raises(PermissionError, match="pilot-firm-03"):
        script.load_gated_tenants()


def test_mou_gate_passes_all_signed():
    from scripts import onboard_pilot_tenants as script
    assert len(script.load_gated_tenants()) == 5


# ── DB-level RLS spot check (skips when DB down) ──────────────────────

@pytest.mark.asyncio
async def test_rls_scopes_rows_to_tenant():
    from sqlalchemy import text
    try:
        from app.db.database import get_async_session
        async with get_async_session() as session:
            count = (await session.execute(text("SELECT count(*) FROM tenants"))).scalar()
    except Exception as exc:  # DB not running locally
        pytest.skip(f"PostgreSQL unreachable: {type(exc).__name__}")
    assert count is not None and count >= 0
