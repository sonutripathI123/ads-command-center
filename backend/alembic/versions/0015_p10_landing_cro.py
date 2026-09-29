"""P10: landing_page_checks, cro_findings, implementation_briefs

Revision ID: 0015_p10
Revises: 0014_p20
Create Date: 2026-09-29

Owning module: P10
Rollback/recovery notes: downgrade drops all landing-page checks, CRO findings and implementation briefs. Nothing on the
websites or in Google Ads is affected; re-run "Check landing pages" to recreate findings. Download briefs (markdown)
first if they are still needed.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P10"

revision = "0015_p10"
down_revision = "0014_p20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "landing_page_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("run_key", sa.String(32), nullable=False, index=True),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("final_url", sa.String(1024)),
        sa.Column("status_code", sa.Integer()),
        sa.Column("elapsed_ms", sa.Float()),
        sa.Column("error", sa.Text()),
        sa.Column("signals", sa.Text()),
        sa.Column("context", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked_by", sa.String(255)),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "cro_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("landing_page_checks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("code", sa.String(48), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("recommendation", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "implementation_briefs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("landing_page_checks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("model", sa.String(64)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("implementation_briefs")
    op.drop_table("cro_findings")
    op.drop_table("landing_page_checks")
