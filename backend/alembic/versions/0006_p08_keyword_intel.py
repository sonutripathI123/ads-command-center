"""P08: search_term_classifications, negative_keyword_candidates, keyword_candidates

Revision ID: 0006_p08
Revises: 0005_p21
Create Date: 2026-09-28

Owning module: P08
Rollback/recovery notes: downgrade drops the three tables. Classifications and candidates are recomputed by
"Run analysis", but review decisions (accepted/rejected, who, when) are lost — export accepted negatives
(GET /api/v1/keywords/accounts/{id}/negatives/export) before downgrading.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P08"

revision = "0006_p08"
down_revision = "0005_p21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_term_classifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("term", sa.String(512), nullable=False),
        sa.Column("intent", sa.String(32), nullable=False),
        sa.Column("business_value", sa.String(16), nullable=False),
        sa.Column("reasons", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("rules_version_note", sa.String(64)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "term"),
    )
    op.create_table(
        "negative_keyword_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("text", sa.String(512), nullable=False),
        sa.Column("match_type", sa.String(8), nullable=False),
        sa.Column("campaign_key", sa.String(32), nullable=False, server_default=""),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Float(), nullable=False, server_default="0"),
        sa.Column("term_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("examples", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("window_from", sa.Date(), nullable=False),
        sa.Column("window_to", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="proposed"),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "text", "match_type", "campaign_key"),
    )
    op.create_table(
        "keyword_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("text", sa.String(512), nullable=False),
        sa.Column("suggested_match_type", sa.String(8), nullable=False, server_default="PHRASE"),
        sa.Column("campaign_google_id", sa.String(32), nullable=False),
        sa.Column("ad_group_google_id", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="proposed"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "text", "ad_group_google_id"),
    )


def downgrade() -> None:
    for t in ("keyword_candidates", "negative_keyword_candidates", "search_term_classifications"):
        op.drop_table(t)
