"""P11: competitors, competitor_observations, competitor_analyses

Revision ID: 0016_p11
Revises: 0015_p10
Create Date: 2026-09-29

Owning module: P11
Rollback/recovery notes: downgrade drops the competitor list, every website/Google observation (including manual SERP
notes, which cannot be re-fetched) and all interpretations. Website observations can be recreated by re-adding the
competitors and re-running research; manual observations are lost.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P11"

revision = "0016_p11"
down_revision = "0015_p10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("brand_terms", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("last_researched_at", sa.DateTime(timezone=True)),
        sa.Column("research_notes", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "domain", name="uq_competitor_account_domain"),
    )
    op.create_table(
        "competitor_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), sa.ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("source", sa.String(1024), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("data", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "competitor_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("model", sa.String(64)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("observation_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("competitor_analyses")
    op.drop_table("competitor_observations")
    op.drop_table("competitors")
