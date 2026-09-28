"""P09: ad_drafts, claim_checks

Revision ID: 0011_p09
Revises: 0010_p14
Create Date: 2026-09-28

Owning module: P09
Rollback/recovery notes: downgrade drops both tables — every ad draft (including AI-written copy and review
status) is lost. Export approved drafts first (GET /api/v1/creatives/accounts/{id}/drafts/export).
"""
from alembic import op
import sqlalchemy as sa

module_id = "P09"

revision = "0011_p09"
down_revision = "0010_p14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ad_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("campaign_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("ad_group_google_id", sa.String(32)),
        sa.Column("ad_group_name", sa.String(255), nullable=False),
        sa.Column("final_url", sa.String(1024), nullable=False, server_default=""),
        sa.Column("keywords", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("usps", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("headlines", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("descriptions", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("path1", sa.String(32), nullable=False, server_default=""),
        sa.Column("path2", sa.String(32), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("model", sa.String(64)),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("strength", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(255)),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "claim_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("ad_drafts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("field", sa.String(16), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("code", sa.String(48), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("claim_checks")
    op.drop_table("ad_drafts")
