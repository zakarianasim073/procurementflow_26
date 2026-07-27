"""Regulatory Compliance Engine: versioned rule registry and audit trail.

Every procurement decision (SLT/ALT, bid security, arithmetic tolerance,
eligibility, TEC scoring, ...) must be traceable to a specific Rule/RuleVersion,
which cites specific Clauses of a specific RegulationVersion, and every
evaluation is persisted as a RuleExecutionLog row — the legal audit trail.

Formula representation is parameterized (formula_kind + parameters JSON),
never eval/exec: app/services/regulatory/formulas.py has exactly one Python
function per formula_kind.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Legal source of truth ────────────────────────────────────────────────

class RegulationDocument(Base):
    """A named body of procurement law (e.g. 'PPR2025', 'PPR2008')."""

    __tablename__ = "regulation_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    issuing_authority: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    versions: Mapped[List["RegulationVersion"]] = relationship("RegulationVersion", back_populates="document")

    __table_args__ = (
        Index("ix_regdocs_code", "code"),
    )


class RegulationVersion(Base):
    """A dated version of a RegulationDocument. Point-in-time rule resolution
    keys off [effective_from, superseded_date) on this table."""

    __tablename__ = "regulation_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulation_documents.id"), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    superseded_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    document: Mapped["RegulationDocument"] = relationship("RegulationDocument", back_populates="versions")
    clauses: Mapped[List["Clause"]] = relationship("Clause", back_populates="regulation_version")

    __table_args__ = (
        Index("ix_regversion_doc_effective", "document_id", "effective_from"),
        CheckConstraint(
            "superseded_date IS NULL OR superseded_date > effective_from",
            name="ck_regversion_date_range",
        ),
    )


class Clause(Base):
    """A citable clause/sub-clause within a RegulationVersion (e.g. 'ITT 52.2(a)')."""

    __tablename__ = "clauses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    regulation_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulation_versions.id"), nullable=False, index=True)
    clause_ref: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_ref: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    regulation_version: Mapped["RegulationVersion"] = relationship("RegulationVersion", back_populates="clauses")

    __table_args__ = (
        Index("ix_clause_version_ref", "regulation_version_id", "clause_ref"),
    )


class Amendment(Base):
    """A dated amendment to a clause within a RegulationVersion."""

    __tablename__ = "amendments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    regulation_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulation_versions.id"), nullable=False, index=True)
    clause_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("clauses.id"), nullable=True, index=True)
    amendment_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Circular(Base):
    """A government circular that may affect one or more Rules.

    affects_rule_ids is populated by MANUAL entry (rule-author review), not
    automated PDF extraction — see plan Section G (out of scope for this pass).
    """

    __tablename__ = "circulars"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    circular_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    issuing_authority: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affects_rule_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ── Rule Registry ────────────────────────────────────────────────────────

class Rule(Base):
    """A single machine-readable procurement rule (e.g. 'PPR2025.SLT_ALT.001').

    A Rule is the stable identity; RuleVersion carries the actual parameters
    and can change over time / across regulation versions without changing
    the Rule's rule_id.
    """

    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_legal_mandate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    procurement_types: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    versions: Mapped[List["RuleVersion"]] = relationship("RuleVersion", back_populates="rule")

    # NOTE: category already has index=True on the column (creates
    # ix_rules_category) — no explicit __table_args__ Index needed (a
    # duplicate-named one breaks create_all with DuplicateTable).


class RuleVersion(Base):
    """A dated, parameterized implementation of a Rule.

    formula_kind selects which function in app/services/regulatory/formulas.py
    evaluates `parameters` against the caller's inputs. Point-in-time
    resolution keys off [effective_from, superseded_date) here, cross-checked
    against the parent RegulationVersion's own bracket.
    """

    __tablename__ = "rule_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rule_id_fk: Mapped[str] = mapped_column(String(36), ForeignKey("rules.id"), nullable=False, index=True)
    regulation_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("regulation_versions.id"), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(50), nullable=False)
    formula_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    explanation_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    superseded_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    rule: Mapped["Rule"] = relationship("Rule", back_populates="versions")
    regulation_version: Mapped["RegulationVersion"] = relationship("RegulationVersion")
    citations: Mapped[List["RuleCitation"]] = relationship("RuleCitation", back_populates="rule_version")

    __table_args__ = (
        Index("ix_ruleversion_rule_effective", "rule_id_fk", "effective_from"),
        Index("ix_ruleversion_status", "status"),
        UniqueConstraint("rule_id_fk", "version_label", name="uq_ruleversion_rule_label"),
        CheckConstraint(
            "status IN ('draft', 'active', 'superseded', 'retired')",
            name="ck_ruleversion_status",
        ),
        CheckConstraint(
            "superseded_date IS NULL OR superseded_date > effective_from",
            name="ck_ruleversion_date_range",
        ),
    )


class RuleCitation(Base):
    """Join table: one RuleVersion can cite multiple clauses/circulars.

    citation_text is denormalized ("ITT 19.1") for fast display without a join.
    """

    __tablename__ = "rule_citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rule_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("rule_versions.id"), nullable=False, index=True)
    clause_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("clauses.id"), nullable=True)
    circular_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("circulars.id"), nullable=True)
    citation_text: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    rule_version: Mapped["RuleVersion"] = relationship("RuleVersion", back_populates="citations")

    __table_args__ = (
        UniqueConstraint("rule_version_id", "citation_text", name="uq_citation_version_text"),
    )


class ProcurementType(Base):
    """Lookup: goods/works/services/consulting x OTM/LTM/RFQ/DPM. Seeded, not
    heavily normalized elsewhere — Rule.procurement_types stores plain `code`
    strings, this table is a reference/display lookup."""

    __tablename__ = "procurement_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    procurement_method: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ── Audit trail ──────────────────────────────────────────────────────────

class RuleExecutionLog(Base):
    """Immutable audit record: one row per RuleEngine.evaluate() call.

    citation_snapshot is frozen at execution time (denormalized copy of the
    RuleVersion's citations) so the audit trail survives later edits to
    Clause/Circular rows — a legally defensible record must reflect what the
    rule said AT THE TIME of the decision, not what it says now.
    """

    __tablename__ = "rule_execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rule_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("rule_versions.id"), nullable=False, index=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    inputs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    intermediate_values: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    outputs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    citation_snapshot: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    actor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_ruleexec_tender", "tender_id"),
        Index("ix_ruleexec_ruleversion_time", "rule_version_id", "executed_at"),
    )
