"""P12: segment_runs, segment_findings

Revision ID: 0021_p12
Revises: 0020_p17
Create Date: 2026-10-05

Owning module: P12
Rollback/recovery notes: downgrade drops stored segment snapshots and findings. They are re-created by running the P12
analysis again (it re-reads Google Ads, read-only), so nothing is lost permanently; Google Ads itself is never touched.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P12"

revision = "0021_p12"
down_revision = "0020_p17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "segment_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "segment_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False, index=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("dimension", sa.String(16), nullable=False),
        sa.Column("segment", sa.String(255), nullable=False),
        sa.Column("code", sa.String(48), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("proposed_action", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(8), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("segment_findings")
    op.drop_table("segment_runs")
