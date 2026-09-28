"""P07: audit_runs, audit_issues

Revision ID: 0009_p07
Revises: 0008_p06
Create Date: 2026-09-28

Owning module: P07
Rollback/recovery notes: downgrade drops both tables. Audits are recomputed with "Run audit"; dismissals
(who dismissed what, and why) are lost.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P07"

revision = "0009_p07"
down_revision = "0008_p06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ads_account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("website_id", sa.Integer()),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("counts", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("errors", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("triggered_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ads_account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("fingerprint", sa.String(600), nullable=False, index=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("risk", sa.String(16), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False, server_default="account"),
        sa.Column("entity_id", sa.String(512), nullable=False, server_default=""),
        sa.Column("link", sa.String(255)),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("dismissed_by", sa.String(255)),
        sa.Column("dismiss_note", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("audit_issues")
    op.drop_table("audit_runs")
