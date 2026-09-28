"""P21: business_rules and business_rule_versions

Revision ID: 0005_p21
Revises: 0004_p05
Create Date: 2026-09-28

Owning module: P21
Rollback/recovery notes: downgrade drops both tables — every saved rules version is lost and analysis falls
back to the built-in defaults. Export first if needed:  GET /api/v1/business-rules/versions (+ each version).
"""
from alembic import op
import sqlalchemy as sa

module_id = "P21"

revision = "0005_p21"
down_revision = "0004_p05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_rules",
        sa.Column("scope", sa.String(64), primary_key=True),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "business_rule_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(64), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_user_id", sa.Integer()),
        sa.Column("created_by_email", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scope", "version"),
    )


def downgrade() -> None:
    op.drop_table("business_rule_versions")
    op.drop_table("business_rules")
