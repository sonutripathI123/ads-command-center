"""P00: feature_flag_overrides table

Revision ID: 0001_p00
Revises:
Create Date: 2026-09-23

Owning module: P00
Rollback/recovery notes: downgrade drops the table; all flags then resolve to their
declared defaults in docs/modules.json (all default off). No other data is affected.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P00"

revision = "0001_p00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flag_overrides",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("updated_by", sa.String(255)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("feature_flag_overrides")
