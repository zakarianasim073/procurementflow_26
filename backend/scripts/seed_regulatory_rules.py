#!/usr/bin/env python
"""Seed the Regulatory Compliance Engine's rule registry.

Idempotent: safe to run multiple times (get_or_create by unique key). Seeds:
  - regulation_documents: PPR2008, PPR2025
  - regulation_versions: PPR2008 (2008-01-01 .. 2025-09-28), PPR2025 (2025-09-28 ..)
  - clauses referenced by the seeded rules
  - rules + rule_versions for every regulatory formula found in the codebase audit
  - a PPR2008 variant of the SLT/ALT rule (symmetric ±10% cap)

Usage:
  python scripts/seed_regulatory_rules.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session

from app.db.database import get_sync_engine
from app.models.regulatory import (
    Clause, RegulationDocument, RegulationVersion, Rule, RuleCitation, RuleVersion,
)

PPR2025_CUTOVER = date(2025, 9, 28)
PPR2008_ENACTED = date(2008, 1, 1)  # sentinel — only needs to be "before PPR2025_CUTOVER"


def get_or_create(session: Session, model, defaults=None, **lookup):
    instance = session.query(model).filter_by(**lookup).first()
    if instance:
        return instance, False
    params = {**lookup, **(defaults or {})}
    instance = model(**params)
    session.add(instance)
    session.flush()
    return instance, True


def seed_regulation_documents(session: Session):
    ppr2008_doc, _ = get_or_create(
        session, RegulationDocument, code="PPR2008",
        defaults={"title": "Public Procurement Rules 2008", "issuing_authority": "CPTU / IMED"},
    )
    ppr2025_doc, _ = get_or_create(
        session, RegulationDocument, code="PPR2025",
        defaults={"title": "Public Procurement Rules 2025", "issuing_authority": "BPPA / IMED"},
    )
    ppr2008_ver, _ = get_or_create(
        session, RegulationVersion, document_id=ppr2008_doc.id, version_label="2008.1",
        defaults={"effective_from": PPR2008_ENACTED, "superseded_date": PPR2025_CUTOVER, "is_current": False},
    )
    ppr2025_ver, _ = get_or_create(
        session, RegulationVersion, document_id=ppr2025_doc.id, version_label="2025.1",
        defaults={"effective_from": PPR2025_CUTOVER, "superseded_date": None, "is_current": True},
    )
    return ppr2008_ver, ppr2025_ver


def seed_clause(session: Session, regulation_version_id: str, clause_ref: str, title: str = "") -> Clause:
    clause, _ = get_or_create(
        session, Clause, regulation_version_id=regulation_version_id, clause_ref=clause_ref,
        defaults={"title": title},
    )
    return clause


def seed_rule(
    session: Session, rule_id: str, category: str, title: str,
    regulation_version_id: str, version_label: str, formula_kind: str, parameters: dict,
    effective_from: date, superseded_date=None, explanation_template: str = "",
    is_legal_mandate: bool = True, procurement_types=None, citation_refs=None,
    citation_clauses: dict | None = None,
):
    """citation_clauses: {clause_ref: Clause} already-created rows to attach."""
    rule, _ = get_or_create(
        session, Rule, rule_id=rule_id,
        defaults={
            "category": category, "title": title, "is_legal_mandate": is_legal_mandate,
            "procurement_types": procurement_types or [],
        },
    )
    rv, created = get_or_create(
        session, RuleVersion, rule_id_fk=rule.id, regulation_version_id=regulation_version_id,
        version_label=version_label,
        defaults={
            "formula_kind": formula_kind, "parameters": parameters, "status": "active",
            "effective_from": effective_from, "superseded_date": superseded_date,
            "explanation_template": explanation_template,
        },
    )
    if created and citation_refs and citation_clauses:
        for ref in citation_refs:
            clause = citation_clauses.get(ref)
            if clause:
                session.add(RuleCitation(rule_version_id=rv.id, clause_id=clause.id, citation_text=ref))
    return rule, rv


def main():
    engine = get_sync_engine()
    session = Session(engine)
    try:
        ppr2008_ver, ppr2025_ver = seed_regulation_documents(session)
        session.flush()

        clauses = {}
        for ref, title in [
            ("ITT 52.2(a)", "Seriously Low Tender (SLT)"),
            ("ITT 52.2(b)", "Abnormally Low Tender (ALT)"),
            ("ITT 27", "Arithmetic correction of bid prices"),
            ("ITT 19.1", "Bid security amount"),
            ("GCC 66.1", "Performance security amount"),
            ("GCC 72.1", "Advance payment ceiling"),
            ("GCC 68.1", "Retention per invoice"),
            ("GCC 68.2", "Cumulative retention cap"),
            ("ITT 7.1", "Subcontracting limit"),
            ("ITT 6.1", "Joint venture partner limit"),
            ("ITT 14.1(d)", "Tender capacity formula"),
        ]:
            clauses[ref] = seed_clause(session, ppr2025_ver.id, ref, title)
        session.flush()

        # ── PPR2025.SLT_ALT.001 ────────────────────────────────────────
        seed_rule(
            session, "PPR2025.SLT_ALT.001", "slt_alt", "Weighted Average Calculation / SLT-ALT Detection",
            ppr2025_ver.id, "2025.1", "RATIO_THRESHOLD_BAND",
            {
                "numerator_field": "quoted_amount", "denominator_field": "estimated_value",
                "bands": [
                    {"max_ratio": 0.60, "label": "ALT"},
                    {"max_ratio": 0.70, "label": "SLT"},
                    {"max_ratio": None, "label": "Normal"},
                ],
            },
            effective_from=PPR2025_CUTOVER,
            explanation_template=(
                "Your quoted price is {discount_pct:.1f}% below the estimated value "
                "(ratio {ratio:.4f}). Under {citation}, this tender is classified {decision}."
            ),
            citation_refs=["ITT 52.2(a)", "ITT 52.2(b)"], citation_clauses=clauses,
        )
        # PPR2008 variant: symmetric +/-10% cap, not the 70%/60% band test.
        seed_rule(
            session, "PPR2025.SLT_ALT.001", "slt_alt", "Weighted Average Calculation / SLT-ALT Detection",
            ppr2008_ver.id, "2008.1", "RATIO_THRESHOLD_BAND",
            {"numerator_field": "quoted_amount", "denominator_field": "estimated_value", "cap_pct": 0.10, "center": 1.0},
            effective_from=PPR2008_ENACTED, superseded_date=PPR2025_CUTOVER,
            explanation_template="Bid ratio {ratio:.4f} vs the PPR2008 +/-10% cap: {decision}.",
        )

        # ── PPR2025.ARITH.TOLERANCE ────────────────────────────────────
        seed_rule(
            session, "PPR2025.ARITH.TOLERANCE", "arithmetic", "Arithmetic Correction Tolerance",
            ppr2025_ver.id, "2025.1", "ARITHMETIC_ERROR_TOLERANCE",
            {"statistic": "AMOUNT_WEIGHTED", "max_error_pct": 0.20},
            effective_from=PPR2025_CUTOVER,
            explanation_template="Arithmetic correction of {correction_pct:.2f}% (ceiling {max_error_pct:.0f}%) under {citation}: {decision}.",
            citation_refs=["ITT 27"], citation_clauses=clauses,
        )

        # ── Financial security / payment rules (all PERCENTAGE_OF) ─────
        seed_rule(
            session, "PPR2025.SECURITY.BID", "financial_security", "Bid Security Requirement",
            ppr2025_ver.id, "2025.1", "PERCENTAGE_OF",
            {"base_field": "estimated_value", "pct": 0.02, "max_absolute": 5_000_000, "mode": "cap", "actual_field": "submitted_amount"},
            effective_from=PPR2025_CUTOVER,
            explanation_template="Bid security required: BDT {required_amount:,.2f} ({pct:.0%} of estimate, capped) under {citation}. Status: {decision}.",
            citation_refs=["ITT 19.1"], citation_clauses=clauses,
        )
        seed_rule(
            session, "PPR2025.SECURITY.PERFORMANCE", "financial_security", "Performance Security Requirement",
            ppr2025_ver.id, "2025.1", "PERCENTAGE_OF",
            {"base_field": "estimated_value", "pct": 0.05, "mode": "cap", "actual_field": "submitted_amount"},
            effective_from=PPR2025_CUTOVER,
            explanation_template="Performance security required: BDT {required_amount:,.2f} ({pct:.0%} of contract value) under {citation}.",
            citation_refs=["GCC 66.1"], citation_clauses=clauses,
        )
        seed_rule(
            session, "PPR2025.PAYMENT.ADVANCE_MAX", "financial_security", "Advance Payment Ceiling",
            ppr2025_ver.id, "2025.1", "PERCENTAGE_OF",
            {"base_field": "estimated_value", "pct": 0.20, "mode": "min_of"},
            effective_from=PPR2025_CUTOVER,
            explanation_template="Max advance payment BDT {max_advance:,.2f}; recommended BDT {recommended_advance:,.2f} under {citation}.",
            citation_refs=["GCC 72.1"], citation_clauses=clauses,
        )
        seed_rule(
            session, "PPR2025.RETENTION", "financial_security", "Retention Money Rules",
            ppr2025_ver.id, "2025.1", "PERCENTAGE_OF",
            {"base_field": "estimated_value", "pct": 0.05, "cap_pct": 0.10, "mode": "retention"},
            effective_from=PPR2025_CUTOVER,
            explanation_template="Retention deducted BDT {retention_deducted:,.2f} (cap BDT {retention_cap:,.2f}) under {citation}.",
            citation_refs=["GCC 68.1", "GCC 68.2"], citation_clauses=clauses,
        )
        seed_rule(
            session, "PPR2025.SUBCONTRACT.MAX", "financial_security", "Subcontracting Limit",
            ppr2025_ver.id, "2025.1", "PERCENTAGE_OF",
            {"base_field": "estimated_value", "pct": 0.30, "mode": "cap", "actual_field": "submitted_amount"},
            effective_from=PPR2025_CUTOVER,
            explanation_template="Subcontracting limit BDT {required_amount:,.2f} ({pct:.0%} of contract value) under {citation}. Status: {decision}.",
            citation_refs=["ITT 7.1"], citation_clauses=clauses,
        )
        seed_rule(
            session, "PPR2025.JV.MAX_PARTNERS", "financial_security", "Joint Venture Partner Limit",
            ppr2025_ver.id, "2025.1", "MAX_COUNT",
            {"field": "jv_partners", "max": 3},
            effective_from=PPR2025_CUTOVER,
            explanation_template="JV partner count {actual:.0f} (max {max_allowed:.0f}) under {citation}: {decision}.",
            citation_refs=["ITT 6.1"], citation_clauses=clauses,
        )

        # ── Tender capacity ──────────────────────────────────────────
        seed_rule(
            session, "PPR2025.CAPACITY.TENDER", "eligibility", "Tender Capacity Formula",
            ppr2025_ver.id, "2025.1", "TENDER_CAPACITY",
            {
                "turnover_multiplier": 2.0, "min_turnover_ratio": 0.5,
                "experience_years_by_value": [{"threshold": 100_000_000, "years": 5}, {"threshold": 0, "years": 3}],
            },
            effective_from=PPR2025_CUTOVER,
            explanation_template="Tender capacity status {decision} (available capacity BDT {available_capacity:,.2f}) under {citation}.",
            citation_refs=["ITT 14.1(d)"], citation_clauses=clauses,
        )

        # ── TEC schedules (pure relocation of ppr2025_compliance.py values) ─
        seed_rule(
            session, "PPR2025.TEC.SCHEDULE_4", "tec_scoring", "TEC Schedule 4 — Goods",
            ppr2025_ver.id, "2025.1", "SCORE_WEIGHTED_CRITERIA",
            {
                "criteria": {
                    "specification_compliance": {"max": 40, "weight": 0.40},
                    "delivery_schedule": {"max": 25, "weight": 0.25},
                    "warranty": {"max": 15, "weight": 0.15},
                    "after_sales_service": {"max": 10, "weight": 0.10},
                    "past_performance": {"max": 10, "weight": 0.10},
                },
                "pass_pct": 0.70,
            },
            effective_from=PPR2025_CUTOVER,
            explanation_template="TEC Schedule 4 score {overall_pct:.1f}% (pass mark {pass_pct:.0f}%): {decision}.",
        )
        seed_rule(
            session, "PPR2025.TEC.SCHEDULE_5", "tec_scoring", "TEC Schedule 5 — Works",
            ppr2025_ver.id, "2025.1", "SCORE_WEIGHTED_CRITERIA",
            {
                "criteria": {
                    "general_experience": {"max": 15, "weight": 0.15},
                    "specific_experience": {"max": 25, "weight": 0.25},
                    "equipment": {"max": 15, "weight": 0.15},
                    "personnel": {"max": 20, "weight": 0.20},
                    "methodology": {"max": 15, "weight": 0.15},
                    "safety_compliance": {"max": 5, "weight": 0.05},
                    "environmental_compliance": {"max": 5, "weight": 0.05},
                },
                "pass_pct": 0.70,
            },
            effective_from=PPR2025_CUTOVER,
            explanation_template="TEC Schedule 5 score {overall_pct:.1f}% (pass mark {pass_pct:.0f}%): {decision}.",
        )
        seed_rule(
            session, "PPR2025.TEC.SCHEDULE_6", "tec_scoring", "TEC Schedule 6 — Services",
            ppr2025_ver.id, "2025.1", "SCORE_WEIGHTED_CRITERIA",
            {
                "criteria": {
                    "similar_experience": {"max": 30, "weight": 0.30},
                    "team_qualifications": {"max": 20, "weight": 0.20},
                    "proposed_approach": {"max": 20, "weight": 0.20},
                    "local_knowledge": {"max": 15, "weight": 0.15},
                    "quality_assurance": {"max": 10, "weight": 0.10},
                    "resource_availability": {"max": 5, "weight": 0.05},
                },
                "pass_pct": 0.70,
            },
            effective_from=PPR2025_CUTOVER,
            explanation_template="TEC Schedule 6 score {overall_pct:.1f}% (pass mark {pass_pct:.0f}%): {decision}.",
        )

        # ── Eligibility floor (agency practice, no direct ITT citation) ─
        seed_rule(
            session, "PPR2025.ELIG.MIN_ENGINEERS", "eligibility", "Minimum Engineers Floor (Works Tender)",
            ppr2025_ver.id, "2025.1", "MIN_COUNT",
            {"field": "engineers_count", "min": 5},
            effective_from=PPR2025_CUTOVER,
            explanation_template="Engineers on staff: {actual:.0f} (minimum {min_required:.0f}): {decision}.",
        )

        # ── Advisory-only heuristic (NOT a legal mandate) ───────────────
        seed_rule(
            session, "PPR.SLT_ALT.ADVISORY_WEIGHTED_QUOTE", "advisory_heuristic", "Advisory Weighted-Average Bid Quote",
            ppr2025_ver.id, "2025.1", "WEIGHTED_AVERAGE_ADVISORY",
            {"weights": {"oce": 0.2, "bidder_avg": 0.5, "nppi_adjusted": 0.3}, "subtract_stddev": True},
            effective_from=PPR2025_CUTOVER, is_legal_mandate=False,
            explanation_template="Advisory weighted-average quote: BDT {weighted_average:,.2f} (threshold BDT {advisory_threshold:,.2f}).",
        )

        session.commit()
        print("Seed complete.")

        # Report counts.
        from app.models.regulatory import Rule as RuleModel, RuleVersion as RuleVersionModel, Clause as ClauseModel
        print(f"  regulation_documents/versions: 2/2")
        print(f"  clauses: {session.query(ClauseModel).count()}")
        print(f"  rules: {session.query(RuleModel).count()}")
        print(f"  rule_versions: {session.query(RuleVersionModel).count()}")
    finally:
        session.close()


if __name__ == "__main__":
    main()


