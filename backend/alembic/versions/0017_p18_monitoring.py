"""P18: alerts, monitor_checks

Revision ID: 0017_p18
Revises: 0016_p11
Create Date: 2026-09-29

Owning module: P18
Rollback/recovery notes: downgrade drops all alerts (including acknowledgements) and the run history. Nothing else is
affected; re-running the checks recreates alerts for conditions that are still present.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P18"

revision = "0017_p18"
down_revision = "0016_p11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("action", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("link", sa.String(255)),
        sa.Column("status", sa.String(16), nullable=False, server_default="open", index=True),
        sa.Column("occurrences", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_by", sa.String(255)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", sa.String(255)),
    )
    op.create_table(
        "monitor_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("trigger", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("signals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column("run_by", sa.String(255)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("monitor_checks")
    op.drop_table("alerts")
