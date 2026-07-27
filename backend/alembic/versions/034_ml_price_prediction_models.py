"""Add ML price prediction model registry tables (T-023).

tender_price_models and bid_price_models store serialised XGBoost models
and training metadata. Only one row per table has is_active=true at any time.

Created at: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa

revision = "034"
down_revision = "033"


def upgrade():
    op.create_table(
        "tender_price_models",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("model_blob", sa.LargeBinary, nullable=True),
        sa.Column("feature_importance_json", sa.JSON, nullable=True),
        sa.Column("validation_rmse", sa.Float, nullable=True),
        sa.Column("validation_r2", sa.Float, nullable=True),
        sa.Column("training_rmse", sa.Float, nullable=True),
        sa.Column("training_r2", sa.Float, nullable=True),
        sa.Column("training_samples", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tpm_is_active", "tender_price_models", ["is_active"])
    op.create_index("ix_tpm_deployed_at", "tender_price_models", ["deployed_at"])

    op.create_table(
        "bid_price_models",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("model_blob", sa.LargeBinary, nullable=True),
        sa.Column("feature_importance_json", sa.JSON, nullable=True),
        sa.Column("validation_rmse", sa.Float, nullable=True),
        sa.Column("validation_r2", sa.Float, nullable=True),
        sa.Column("training_rmse", sa.Float, nullable=True),
        sa.Column("training_r2", sa.Float, nullable=True),
        sa.Column("training_samples", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bpm_is_active", "bid_price_models", ["is_active"])
    op.create_index("ix_bpm_deployed_at", "bid_price_models", ["deployed_at"])


def downgrade():
    op.drop_table("bid_price_models")
    op.drop_table("tender_price_models")
