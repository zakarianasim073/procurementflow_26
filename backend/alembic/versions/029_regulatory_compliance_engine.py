"""Regulatory Compliance Engine — versioned rule registry + audit trail.

Creates the legal source-of-truth schema for procurement rules:
- regulation_documents / regulation_versions / clauses / amendments / circulars
- rules / rule_versions / rule_citations / procurement_types
- rule_execution_logs (immutable audit trail — one row per RuleEngine.evaluate())

See app/models/regulatory.py for the ORM models and
app/services/regulatory/ for the engine that reads/writes this schema.
"""

from alembic import op
import sqlalchemy as sa

revision = "029_regulatory_compliance_engine"
down_revision = "028"


def upgrade():
    """Create regulatory compliance engine schema."""

    # ── Legal source of truth ──────────────────────────────────────────

    op.create_table(
        "regulation_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("issuing_authority", sa.String(255), nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_regdocs_code", "regulation_documents", ["code"])

    op.create_table(
        "regulation_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("regulation_documents.id"), nullable=False),
        sa.Column("version_label", sa.String(50), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("superseded_date", sa.Date, nullable=True),
        sa.Column("is_current", sa.Boolean, default=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_regversion_document_id", "regulation_versions", ["document_id"])
    op.create_index("ix_regversion_effective_from", "regulation_versions", ["effective_from"])
    op.create_index("ix_regversion_superseded_date", "regulation_versions", ["superseded_date"])
    op.create_index("ix_regversion_doc_effective", "regulation_versions", ["document_id", "effective_from"])

    op.create_table(
        "clauses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("regulation_version_id", sa.String(36), sa.ForeignKey("regulation_versions.id"), nullable=False),
        sa.Column("clause_ref", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("full_text", sa.Text, nullable=True),
        sa.Column("page_ref", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_clause_regulation_version_id", "clauses", ["regulation_version_id"])
    op.create_index("ix_clause_version_ref", "clauses", ["regulation_version_id", "clause_ref"])

    op.create_table(
        "amendments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("regulation_version_id", sa.String(36), sa.ForeignKey("regulation_versions.id"), nullable=False),
        sa.Column("clause_id", sa.String(36), sa.ForeignKey("clauses.id"), nullable=True),
        sa.Column("amendment_ref", sa.String(100), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_amendment_regulation_version_id", "amendments", ["regulation_version_id"])
    op.create_index("ix_amendment_effective_date", "amendments", ["effective_date"])

    op.create_table(
        "circulars",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("circular_no", sa.String(100), nullable=False, unique=True),
        sa.Column("issuing_authority", sa.String(255), nullable=True),
        sa.Column("issue_date", sa.Date, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("affects_rule_ids", sa.JSON, default=list),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_circular_issue_date", "circulars", ["issue_date"])

    # ── Rule registry ───────────────────────────────────────────────────

    op.create_table(
        "rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(100), nullable=False, unique=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_legal_mandate", sa.Boolean, default=True),
        sa.Column("procurement_types", sa.JSON, default=list),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rules_rule_id", "rules", ["rule_id"])
    op.create_index("ix_rules_category", "rules", ["category"])

    op.create_table(
        "rule_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id_fk", sa.String(36), sa.ForeignKey("rules.id"), nullable=False),
        sa.Column("regulation_version_id", sa.String(36), sa.ForeignKey("regulation_versions.id"), nullable=False),
        sa.Column("version_label", sa.String(50), nullable=False),
        sa.Column("formula_kind", sa.String(30), nullable=False),
        sa.Column("parameters", sa.JSON, nullable=False),
        sa.Column("explanation_template", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("superseded_date", sa.Date, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ruleversion_rule_id_fk", "rule_versions", ["rule_id_fk"])
    op.create_index("ix_ruleversion_regulation_version_id", "rule_versions", ["regulation_version_id"])
    op.create_index("ix_ruleversion_effective_from", "rule_versions", ["effective_from"])
    op.create_index("ix_ruleversion_superseded_date", "rule_versions", ["superseded_date"])
    op.create_index("ix_ruleversion_rule_effective", "rule_versions", ["rule_id_fk", "effective_from"])
    op.create_index("ix_ruleversion_status", "rule_versions", ["status"])

    op.create_table(
        "rule_citations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_version_id", sa.String(36), sa.ForeignKey("rule_versions.id"), nullable=False),
        sa.Column("clause_id", sa.String(36), sa.ForeignKey("clauses.id"), nullable=True),
        sa.Column("circular_id", sa.String(36), sa.ForeignKey("circulars.id"), nullable=True),
        sa.Column("citation_text", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rulecitation_rule_version_id", "rule_citations", ["rule_version_id"])

    op.create_table(
        "procurement_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("procurement_method", sa.String(30), nullable=True),
        sa.Column("label", sa.String(100), nullable=False),
    )

    # ── Audit trail ─────────────────────────────────────────────────────

    op.create_table(
        "rule_execution_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_version_id", sa.String(36), sa.ForeignKey("rule_versions.id"), nullable=False),
        sa.Column("tender_id", sa.String(100), nullable=True),
        sa.Column("agent_id", sa.String(100), nullable=True),
        sa.Column("trace_id", sa.String(36), nullable=True),
        sa.Column("request_id", sa.String(36), nullable=True),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("inputs", sa.JSON, nullable=False),
        sa.Column("intermediate_values", sa.JSON, default=dict),
        sa.Column("outputs", sa.JSON, nullable=False),
        sa.Column("decision", sa.String(50), nullable=True),
        sa.Column("citation_snapshot", sa.JSON, default=list),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actor", sa.String(100), nullable=True),
    )
    op.create_index("ix_ruleexec_rule_version_id", "rule_execution_logs", ["rule_version_id"])
    op.create_index("ix_ruleexec_tender", "rule_execution_logs", ["tender_id"])
    op.create_index("ix_ruleexec_agent_id", "rule_execution_logs", ["agent_id"])
    op.create_index("ix_ruleexec_trace_id", "rule_execution_logs", ["trace_id"])
    op.create_index("ix_ruleexec_tenant_id", "rule_execution_logs", ["tenant_id"])
    op.create_index("ix_ruleexec_executed_at", "rule_execution_logs", ["executed_at"])
    op.create_index("ix_ruleexec_ruleversion_time", "rule_execution_logs", ["rule_version_id", "executed_at"])


def downgrade():
    """Drop regulatory compliance engine schema."""
    op.drop_table("rule_execution_logs")
    op.drop_table("procurement_types")
    op.drop_table("rule_citations")
    op.drop_table("rule_versions")
    op.drop_table("rules")
    op.drop_table("circulars")
    op.drop_table("amendments")
    op.drop_table("clauses")
    op.drop_table("regulation_versions")
    op.drop_table("regulation_documents")
