"""Analytics Data Warehouse - Star Schema (T-020)."""

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Create analytics warehouse schema."""

    # ── Dimension Tables (slowly changing dimensions) ────────────────────

    # Agencies dimension
    op.create_table(
        "dim_agencies",
        sa.Column("agency_id", sa.String(36), primary_key=True),
        sa.Column("agency_code", sa.String(50), nullable=False),
        sa.Column("agency_name", sa.String(255), nullable=False),
        sa.Column("division", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("last_tender_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_spend_bdt", sa.Numeric(15, 2), default=0),
        sa.Column("tender_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dim_agencies_code", "dim_agencies", ["agency_code"])
    op.create_index("ix_dim_agencies_division", "dim_agencies", ["division"])

    # Zones dimension
    op.create_table(
        "dim_zones",
        sa.Column("zone_id", sa.String(10), primary_key=True),
        sa.Column("zone_name", sa.String(100), nullable=False),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("agency_type", sa.String(50), nullable=True),  # LGED, PWD, BWDB
        sa.Column("tender_count", sa.Integer, default=0),
        sa.Column("total_spend_bdt", sa.Numeric(15, 2), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dim_zones_region", "dim_zones", ["region"])
    op.create_index("ix_dim_zones_type", "dim_zones", ["agency_type"])

    # Categories/Sectors dimension
    op.create_table(
        "dim_categories",
        sa.Column("category_id", sa.String(36), primary_key=True),
        sa.Column("category_name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("subsector", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tender_count", sa.Integer, default=0),
        sa.Column("avg_tender_value_bdt", sa.Numeric(15, 2), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dim_categories_sector", "dim_categories", ["sector"])

    # Contractors dimension
    op.create_table(
        "dim_contractors",
        sa.Column("contractor_id", sa.String(36), primary_key=True),
        sa.Column("contractor_name", sa.String(255), nullable=False),
        sa.Column("registration_number", sa.String(100), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("zone", sa.String(10), nullable=True),
        sa.Column("bid_count", sa.Integer, default=0),
        sa.Column("award_count", sa.Integer, default=0),
        sa.Column("total_contract_value_bdt", sa.Numeric(15, 2), default=0),
        sa.Column("completion_rate_pct", sa.Numeric(5, 2), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dim_contractors_name", "dim_contractors", ["contractor_name"])
    op.create_index("ix_dim_contractors_zone", "dim_contractors", ["zone"])

    # ── Fact Tables (immutable events) ───────────────────────────────────

    # Fact: Tenders
    op.create_table(
        "fact_tenders",
        sa.Column("tender_id", sa.String(36), primary_key=True),
        sa.Column("agency_id", sa.String(36), sa.ForeignKey("dim_agencies.agency_id")),
        sa.Column("zone_id", sa.String(10), sa.ForeignKey("dim_zones.zone_id")),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("dim_categories.category_id")),
        sa.Column("tender_value_bdt", sa.Numeric(15, 2), nullable=True),
        sa.Column("estimated_value_bdt", sa.Numeric(15, 2), nullable=True),
        sa.Column("procurement_method", sa.String(50), nullable=True),
        sa.Column("tender_type", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), default="open"),
        sa.Column("published_date", sa.Date, nullable=True),
        sa.Column("deadline_date", sa.Date, nullable=True),
        sa.Column("award_date", sa.Date, nullable=True),
        sa.Column("completion_date", sa.Date, nullable=True),
        sa.Column("bid_count", sa.Integer, default=0),
        sa.Column("duration_days", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fact_tenders_agency", "fact_tenders", ["agency_id"])
    op.create_index("ix_fact_tenders_zone", "fact_tenders", ["zone_id"])
    op.create_index("ix_fact_tenders_category", "fact_tenders", ["category_id"])
    op.create_index("ix_fact_tenders_status", "fact_tenders", ["status"])
    op.create_index("ix_fact_tenders_published", "fact_tenders", ["published_date"])
    op.create_index("ix_fact_tenders_award", "fact_tenders", ["award_date"])

    # Fact: Awards
    op.create_table(
        "fact_awards",
        sa.Column("award_id", sa.String(36), primary_key=True),
        sa.Column("tender_id", sa.String(36), sa.ForeignKey("fact_tenders.tender_id")),
        sa.Column("contractor_id", sa.String(36), sa.ForeignKey("dim_contractors.contractor_id")),
        sa.Column("award_value_bdt", sa.Numeric(15, 2), nullable=True),
        sa.Column("award_date", sa.Date, nullable=True),
        sa.Column("completion_status", sa.String(50), default="pending"),
        sa.Column("days_to_award", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fact_awards_tender", "fact_awards", ["tender_id"])
    op.create_index("ix_fact_awards_contractor", "fact_awards", ["contractor_id"])
    op.create_index("ix_fact_awards_date", "fact_awards", ["award_date"])

    # Fact: Bids
    op.create_table(
        "fact_bids",
        sa.Column("bid_id", sa.String(36), primary_key=True),
        sa.Column("tender_id", sa.String(36), sa.ForeignKey("fact_tenders.tender_id")),
        sa.Column("contractor_id", sa.String(36), sa.ForeignKey("dim_contractors.contractor_id")),
        sa.Column("bid_amount_bdt", sa.Numeric(15, 2), nullable=True),
        sa.Column("bid_date", sa.Date, nullable=True),
        sa.Column("is_winner", sa.Boolean, default=False),
        sa.Column("days_to_bid", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fact_bids_tender", "fact_bids", ["tender_id"])
    op.create_index("ix_fact_bids_contractor", "fact_bids", ["contractor_id"])
    op.create_index("ix_fact_bids_date", "fact_bids", ["bid_date"])
    op.create_index("ix_fact_bids_winner", "fact_bids", ["is_winner"])

    # ── Materialized Views (Pre-computed Aggregations) ────────────────────

    # Market overview by agency
    op.execute("""
        CREATE MATERIALIZED VIEW vw_market_by_agency AS
        SELECT
            a.agency_id,
            a.agency_code,
            a.agency_name,
            COUNT(DISTINCT t.tender_id) as tender_count,
            SUM(t.tender_value_bdt) as total_value_bdt,
            AVG(t.tender_value_bdt) as avg_value_bdt,
            AVG(t.duration_days) as avg_duration_days,
            COUNT(DISTINCT CASE WHEN t.status = 'awarded' THEN t.tender_id END) as awarded_count
        FROM dim_agencies a
        LEFT JOIN fact_tenders t ON a.agency_id = t.agency_id
        GROUP BY a.agency_id, a.agency_code, a.agency_name
        WITH DATA
    """)
    op.create_index("ix_vw_market_agency_id", "vw_market_by_agency", ["agency_id"])

    # Market trends by zone
    op.execute("""
        CREATE MATERIALIZED VIEW vw_market_by_zone AS
        SELECT
            z.zone_id,
            z.zone_name,
            z.region,
            EXTRACT(YEAR_MONTH FROM t.published_date) as year_month,
            COUNT(DISTINCT t.tender_id) as tender_count,
            SUM(t.tender_value_bdt) as total_value_bdt,
            AVG(t.tender_value_bdt) as avg_value_bdt
        FROM dim_zones z
        LEFT JOIN fact_tenders t ON z.zone_id = t.zone_id
        WHERE t.published_date IS NOT NULL
        GROUP BY z.zone_id, z.zone_name, z.region, EXTRACT(YEAR_MONTH FROM t.published_date)
        WITH DATA
    """)

    # Contractor performance
    op.execute("""
        CREATE MATERIALIZED VIEW vw_contractor_performance AS
        SELECT
            c.contractor_id,
            c.contractor_name,
            COUNT(DISTINCT b.bid_id) as total_bids,
            COUNT(DISTINCT CASE WHEN b.is_winner THEN b.bid_id END) as won_bids,
            ROUND(
                100.0 * COUNT(DISTINCT CASE WHEN b.is_winner THEN b.bid_id END)::NUMERIC
                / NULLIF(COUNT(DISTINCT b.bid_id), 0), 2
            ) as win_rate_pct,
            AVG(b.bid_amount_bdt) as avg_bid_amount_bdt,
            AVG(a.award_value_bdt) as avg_award_value_bdt,
            COUNT(DISTINCT a.award_id) as award_count
        FROM dim_contractors c
        LEFT JOIN fact_bids b ON c.contractor_id = b.contractor_id
        LEFT JOIN fact_awards a ON c.contractor_id = a.contractor_id
        GROUP BY c.contractor_id, c.contractor_name
        WITH DATA
    """)
    op.create_index("ix_vw_contractor_perf_id", "vw_contractor_performance", ["contractor_id"])

    # Time series: Monthly tender volume
    op.execute("""
        CREATE MATERIALIZED VIEW vw_tender_volume_monthly AS
        SELECT
            DATE_TRUNC('month', t.published_date)::DATE as month,
            z.zone_id,
            COUNT(DISTINCT t.tender_id) as tender_count,
            SUM(t.tender_value_bdt) as total_value_bdt,
            AVG(t.tender_value_bdt) as avg_value_bdt
        FROM fact_tenders t
        LEFT JOIN dim_zones z ON t.zone_id = z.zone_id
        WHERE t.published_date IS NOT NULL
        GROUP BY DATE_TRUNC('month', t.published_date), z.zone_id
        WITH DATA
    """)

    # Category trends
    op.execute("""
        CREATE MATERIALIZED VIEW vw_category_trends AS
        SELECT
            c.category_id,
            c.category_name,
            c.sector,
            DATE_TRUNC('month', t.published_date)::DATE as month,
            COUNT(DISTINCT t.tender_id) as tender_count,
            SUM(t.tender_value_bdt) as total_value_bdt,
            AVG(t.tender_value_bdt) as avg_value_bdt
        FROM fact_tenders t
        LEFT JOIN dim_categories c ON t.category_id = c.category_id
        WHERE t.published_date IS NOT NULL
        GROUP BY c.category_id, c.category_name, c.sector, DATE_TRUNC('month', t.published_date)
        WITH DATA
    """)


def downgrade():
    """Drop analytics warehouse."""

    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vw_category_trends")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vw_tender_volume_monthly")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vw_contractor_performance")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vw_market_by_zone")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS vw_market_by_agency")

    # Drop fact tables
    op.drop_table("fact_bids")
    op.drop_table("fact_awards")
    op.drop_table("fact_tenders")

    # Drop dimension tables
    op.drop_table("dim_contractors")
    op.drop_table("dim_categories")
    op.drop_table("dim_zones")
    op.drop_table("dim_agencies")
