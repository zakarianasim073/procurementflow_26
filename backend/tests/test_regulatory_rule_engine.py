"""Boundary/negative tests for the Regulatory Compliance Engine.

Requires scripts/seed_regulatory_rules.py to have been run against the
local DB (tables + seed rows). These are integration tests against the real
rule_engine + PostgreSQL, matching this repo's existing test convention
(see test_tenant_rbac_and_decision_calibration.py) — no mocking of the DB.
"""
from __future__ import annotations

from datetime import date

from app.services.regulatory import rule_engine


# ── SLT/ALT ratio boundaries (ITT 52.2) ──────────────────────────────────

def test_ratio_exactly_at_slt_threshold_is_normal():
    """Boundary is `<`, not `<=` — a ratio of exactly 0.70 is NOT SLT."""
    r = rule_engine.check_slt_alt(quoted_amount=7_000_000, estimated_value=10_000_000, tender_date=date(2026, 1, 1))
    assert r.decision == "Normal"
    assert r.passed is True


def test_ratio_just_below_slt_threshold_is_slt():
    r = rule_engine.check_slt_alt(quoted_amount=6_999_999, estimated_value=10_000_000, tender_date=date(2026, 1, 1))
    assert r.decision == "SLT"
    assert r.passed is False


def test_ratio_exactly_at_alt_threshold_is_slt():
    """0.60 exactly is still SLT (not yet ALT) — ALT boundary is also `<`."""
    r = rule_engine.check_slt_alt(quoted_amount=6_000_000, estimated_value=10_000_000, tender_date=date(2026, 1, 1))
    assert r.decision == "SLT"


def test_ratio_just_below_alt_threshold_is_alt():
    r = rule_engine.check_slt_alt(quoted_amount=5_999_999, estimated_value=10_000_000, tender_date=date(2026, 1, 1))
    assert r.decision == "ALT"
    assert r.passed is False


# ── Arithmetic error tolerance (ITT 27) ──────────────────────────────────

def test_arithmetic_correction_exactly_20pct_is_acceptable():
    """Boundary is `>`, not `>=` — exactly 20% is NOT rejectable.
    correction_pct = variance / stated_amount * 100; qty*rate=1200,
    stated=1000 -> variance=200 -> 200/1000 = 20.0% exactly."""
    boq = [{"item_no": 1, "qty": 1, "rate": 1200, "amount": 1000}]
    r = rule_engine.check_arithmetic_tolerance(boq, tender_date=date(2026, 1, 1))
    assert r.outputs["correction_pct"] == 20.0
    assert r.decision == "ACCEPTABLE"
    assert r.passed is True


def test_arithmetic_correction_just_over_20pct_is_rejectable():
    boq = [{"item_no": 1, "qty": 1, "rate": 1000, "amount": 799}]  # 201/1000 = 20.1%
    r = rule_engine.check_arithmetic_tolerance(boq, tender_date=date(2026, 1, 1))
    assert r.outputs["correction_pct"] > 20.0
    assert r.decision == "REJECTABLE"
    assert r.passed is False


# ── Bid security (ITT 19.1) — confirms the 1%/2% contradiction was resolved ──

def test_bid_security_at_new_2pct_is_adequate():
    r = rule_engine.check_bid_security(estimated_value=10_000_000, submitted_amount=200_000, tender_date=date(2026, 1, 1))
    assert r.outputs["required_amount"] == 200_000.0
    assert r.passed is True


def test_bid_security_at_old_1pct_now_fails():
    """The old uncited 1% literal must now be INADEQUATE — proves the
    contradiction (ppr_engine.py's cited 2% vs ppr_evaluation.py's uncited
    1%) was actually resolved to 2%, not silently left at the old value."""
    r = rule_engine.check_bid_security(estimated_value=10_000_000, submitted_amount=100_000, tender_date=date(2026, 1, 1))
    assert r.passed is False
    assert r.outputs["required_amount"] == 200_000.0


# ── Point-in-time regulation resolution ──────────────────────────────────

def test_tender_before_cutover_resolves_ppr2008():
    r = rule_engine.check_slt_alt(quoted_amount=9_000_000, estimated_value=10_000_000, tender_date=date(2025, 9, 27))
    assert r.rule_version_label == "2008.1"


def test_tender_on_cutover_date_resolves_ppr2025():
    """Cutover boundary is inclusive (>=), matching regime.py's existing semantics."""
    r = rule_engine.check_slt_alt(quoted_amount=9_000_000, estimated_value=10_000_000, tender_date=date(2025, 9, 28))
    assert r.rule_version_label == "2025.1"


def test_ppr2008_uses_symmetric_cap_not_ratio_bands():
    """PPR2008's SLT/ALT rule is a totally different formula (+/-10% cap
    around 1.0), not the 70%/60% band test — 90% ratio is within-cap Normal
    under PPR2008 even though it would be far below SLT under PPR2025."""
    r = rule_engine.check_slt_alt(quoted_amount=9_000_000, estimated_value=10_000_000, tender_date=date(2020, 1, 1))
    assert r.decision == "Normal"
    assert r.rule_version_label == "2008.1"

    r2 = rule_engine.check_slt_alt(quoted_amount=8_000_000, estimated_value=10_000_000, tender_date=date(2020, 1, 1))
    assert r2.decision == "BelowCap"


# ── Audit trail ───────────────────────────────────────────────────────────

def test_evaluate_always_writes_an_execution_log():
    r = rule_engine.check_slt_alt(
        quoted_amount=9_500_000, estimated_value=10_000_000, tender_date=date(2026, 1, 1),
        tender_id="TEST-AUDIT-1", agent_id="test_regulatory_rule_engine",
    )
    assert r.execution_log_id  # non-empty — a RuleExecutionLog row was persisted
    assert r.citations  # ITT 52.2(a)/(b)


def test_advisory_rule_is_not_a_legal_mandate_but_still_executes():
    r = rule_engine.advisory_weighted_quote(
        oce=10_000_000, nppi=0.91, bidder_prices=[9_400_000, 9_500_000, 9_600_000],
        tender_date=date(2026, 1, 1),
    )
    assert r.decision == "ADVISORY"
    assert r.passed is True  # informational, not a gate
    assert r.outputs["weighted_average"] > 0
