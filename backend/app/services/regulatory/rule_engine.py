"""Rule Engine — the single source of truth for procurement compliance decisions.

No application code should contain procurement formulas directly. Agents and
services call this module's `rule_engine` singleton, which:
  1. Resolves the applicable RuleVersion for a rule_id at a given tender_date
     (point-in-time resolution — a 2023 tender always gets PPR2008 rules, a
     2026 tender always gets PPR2025 rules).
  2. Dispatches to app.services.regulatory.formulas[formula_kind].
  3. ALWAYS persists a RuleExecutionLog row (the legal audit trail) — never
     optional, since audit-trail loss is a compliance issue, not a cosmetic one.
  4. Returns a RuleExecutionResult with decision, outputs, citations, and a
     rendered explanation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_sync_engine
from app.models.regulatory import Rule, RuleCitation, RuleExecutionLog, RuleVersion
from app.services.regulatory.explain import render_explanation
from app.services.regulatory.formulas import FORMULA_REGISTRY

logger = logging.getLogger(__name__)


@dataclass
class RuleExecutionResult:
    """Standard result of a single rule evaluation — reshape this into any
    caller's existing return-dict/AgentResult.output shape at the call site."""
    rule_id: str = ""
    rule_version_label: str = ""
    decision: str = ""
    passed: bool = False
    outputs: Dict[str, Any] = field(default_factory=dict)
    intermediate_values: Dict[str, Any] = field(default_factory=dict)
    citations: List[str] = field(default_factory=list)
    explanation: str = ""
    execution_log_id: str = ""


class RuleNotFoundError(RuntimeError):
    """No active RuleVersion resolves for the given rule_id at the given date."""


def _to_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.fromisoformat(value[:10]).date()
    return date.today()


class RuleEngine:
    def _resolve_rule_version(self, session: Session, rule_id: str, tender_date: date) -> Optional[RuleVersion]:
        rv = session.execute(
            select(RuleVersion)
            .join(Rule, RuleVersion.rule_id_fk == Rule.id)
            .where(
                Rule.rule_id == rule_id,
                RuleVersion.status == "active",
                RuleVersion.effective_from <= tender_date,
            )
            .order_by(RuleVersion.effective_from.desc())
        ).scalars().first()
        if rv is None:
            return None
        if rv.superseded_date is not None and rv.superseded_date <= tender_date:
            return None
        return rv

    def resolve_applicable_rules(
        self,
        procurement_type: str,
        tender_date,
        category: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[RuleVersion]:
        """Return every active RuleVersion applicable to a procurement_type at tender_date."""
        tender_date = _to_date(tender_date)
        session = get_sync_session_instance()
        try:
            query = (
                select(RuleVersion)
                .join(Rule, RuleVersion.rule_id_fk == Rule.id)
                .where(
                    RuleVersion.status == "active",
                    RuleVersion.effective_from <= tender_date,
                )
            )
            if category:
                query = query.where(Rule.category == category)
            rows = session.execute(query).scalars().all()
            applicable = []
            for rv in rows:
                if rv.superseded_date is not None and rv.superseded_date <= tender_date:
                    continue
                rule = session.get(Rule, rv.rule_id_fk)
                if rule and rule.procurement_types and procurement_type not in rule.procurement_types:
                    continue
                applicable.append(rv)
            return applicable
        finally:
            session.close()

    def get_parameter(self, rule_id: str, param_names: List[str], tender_date) -> Dict[str, Any]:
        """Read-only parameter lookup — no audit log written. For hot paths
        (e.g. ML feature labeling) that would otherwise flood rule_execution_logs."""
        tender_date = _to_date(tender_date)
        session = get_sync_session_instance()
        try:
            rv = self._resolve_rule_version(session, rule_id, tender_date)
            if rv is None:
                return {}
            return {name: rv.parameters.get(name) for name in param_names if name in rv.parameters}
        except Exception as exc:
            logger.warning("get_parameter(%s) failed: %s", rule_id, exc)
            return {}
        finally:
            session.close()

    def evaluate(
        self,
        rule_id: str,
        inputs: Dict[str, Any],
        tender_date,
        *,
        tenant_id: Optional[str] = None,
        tender_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> RuleExecutionResult:
        tender_date = _to_date(tender_date)
        session = get_sync_session_instance()
        try:
            rv = self._resolve_rule_version(session, rule_id, tender_date)
            if rv is None:
                raise RuleNotFoundError(
                    f"No active RuleVersion for rule_id={rule_id!r} at tender_date={tender_date}"
                )

            formula_fn = FORMULA_REGISTRY.get(rv.formula_kind)
            if formula_fn is None:
                raise RuleNotFoundError(f"Unknown formula_kind={rv.formula_kind!r} for rule_id={rule_id!r}")

            raw = formula_fn(inputs, rv.parameters)

            citation_rows = session.execute(
                select(RuleCitation).where(RuleCitation.rule_version_id == rv.id)
            ).scalars().all()
            citations = [c.citation_text for c in citation_rows]

            explanation = render_explanation(
                rv.explanation_template,
                decision=raw.get("decision", ""),
                outputs=raw.get("outputs", {}),
                intermediate_values=raw.get("intermediate_values", {}),
                citations=citations,
            )

            log_id = ""
            try:
                log_row = RuleExecutionLog(
                    rule_version_id=rv.id,
                    tender_id=tender_id,
                    agent_id=agent_id,
                    trace_id=trace_id,
                    request_id=request_id,
                    tenant_id=tenant_id,
                    inputs=inputs,
                    intermediate_values=raw.get("intermediate_values", {}),
                    outputs=raw.get("outputs", {}),
                    decision=raw.get("decision", ""),
                    citation_snapshot=citations,
                    actor=actor,
                )
                session.add(log_row)
                session.commit()
                log_id = log_row.id
            except Exception as exc:
                # Audit-trail loss is a compliance issue, not cosmetic — log
                # loudly, but do not fail the evaluation because logging failed.
                session.rollback()
                logger.error("Failed to persist RuleExecutionLog for rule_id=%s: %s", rule_id, exc)

            return RuleExecutionResult(
                rule_id=rule_id,
                rule_version_label=rv.version_label,
                decision=raw.get("decision", ""),
                passed=bool(raw.get("passed", False)),
                outputs=raw.get("outputs", {}),
                intermediate_values=raw.get("intermediate_values", {}),
                citations=citations,
                explanation=explanation,
                execution_log_id=log_id,
            )
        finally:
            session.close()

    # ── Thin convenience wrappers — each calls evaluate() with a fixed
    # rule_id; NOT separate implementations (one rule, one formula). ──────

    def check_slt_alt(self, quoted_amount, estimated_value, tender_date, **ctx) -> RuleExecutionResult:
        return self.evaluate(
            "PPR2025.SLT_ALT.001",
            {"quoted_amount": quoted_amount, "estimated_value": estimated_value},
            tender_date, **ctx,
        )

    def check_bid_security(self, estimated_value, submitted_amount, tender_date, **ctx) -> RuleExecutionResult:
        return self.evaluate(
            "PPR2025.SECURITY.BID",
            {"estimated_value": estimated_value, "submitted_amount": submitted_amount},
            tender_date, **ctx,
        )

    def check_arithmetic_tolerance(self, boq_items, tender_date, **ctx) -> RuleExecutionResult:
        return self.evaluate("PPR2025.ARITH.TOLERANCE", {"boq_items": boq_items}, tender_date, **ctx)

    def check_performance_security(self, contract_value, tender_date, **ctx) -> RuleExecutionResult:
        return self.evaluate(
            "PPR2025.SECURITY.PERFORMANCE", {"estimated_value": contract_value}, tender_date, **ctx
        )

    def check_advance_payment(self, contract_value, mobilization_required, tender_date, **ctx) -> RuleExecutionResult:
        return self.evaluate(
            "PPR2025.PAYMENT.ADVANCE_MAX",
            {"estimated_value": contract_value, "mobilization_required": mobilization_required},
            tender_date, **ctx,
        )

    def check_retention(self, monthly_invoices, tender_date, **ctx) -> RuleExecutionResult:
        return self.evaluate(
            "PPR2025.RETENTION", {"monthly_invoices": monthly_invoices, "estimated_value": 0}, tender_date, **ctx
        )

    def check_subcontracting(self, subcontract_amount, contract_value, tender_date, **ctx) -> RuleExecutionResult:
        return self.evaluate(
            "PPR2025.SUBCONTRACT.MAX",
            {"estimated_value": contract_value, "submitted_amount": subcontract_amount},
            tender_date, **ctx,
        )

    def check_tender_capacity(
        self, annual_turnover, current_commitments, tender_estimated_value, years_in_business, tender_date, **ctx
    ) -> RuleExecutionResult:
        return self.evaluate(
            "PPR2025.CAPACITY.TENDER",
            {
                "annual_turnover": annual_turnover,
                "current_commitments": current_commitments,
                "tender_estimated_value": tender_estimated_value,
                "years_in_business": years_in_business,
            },
            tender_date, **ctx,
        )

    def score_tec_schedule(self, schedule_key: str, vendor_scores: Dict[str, float], tender_date, **ctx) -> RuleExecutionResult:
        rule_id = {
            "schedule_4": "PPR2025.TEC.SCHEDULE_4",
            "schedule_5": "PPR2025.TEC.SCHEDULE_5",
            "schedule_6": "PPR2025.TEC.SCHEDULE_6",
        }.get(schedule_key, schedule_key)
        return self.evaluate(rule_id, {"scores": vendor_scores}, tender_date, **ctx)

    def advisory_weighted_quote(self, oce, nppi, bidder_prices, tender_date, **ctx) -> RuleExecutionResult:
        return self.evaluate(
            "PPR.SLT_ALT.ADVISORY_WEIGHTED_QUOTE",
            {"oce": oce, "nppi": nppi, "bidder_prices": bidder_prices or []},
            tender_date, **ctx,
        )


def get_sync_session_instance() -> Session:
    """Local helper so this module only imports get_sync_engine (matches the
    decision_calibration.py idiom) while still getting a plain ORM Session."""
    return Session(get_sync_engine())


rule_engine = RuleEngine()  # module-level singleton, matches decision_calibration_service pattern
