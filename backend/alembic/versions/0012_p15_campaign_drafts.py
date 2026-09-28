"""P15: campaign_drafts

Revision ID: 0012_p15
Revises: 0011_p09
Create Date: 2026-09-29

Owning module: P15
Rollback/recovery notes: downgrade drops campaign_drafts — every draft campaign structure (ad groups, keyword
moves, negatives, settings, approvals) is lost. Ad copy lives in P09 and is not affected. Export approved drafts
first (GET /api/v1/campaign-builder/drafts/{id}/export).
"""
from alembic import op
import sqlalchemy as sa

module_id = "P15"

revision = "0012_p15"
down_revision = "0011_p09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("website_id", sa.Integer()),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("settings", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("ad_groups", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("unassigned", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("negatives", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("tracking_issues", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(255)),
        sa.Column("approved_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("campaign_drafts")
