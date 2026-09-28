"""P16: approvals, approval_events

Revision ID: 0013_p16
Revises: 0012_p15
Create Date: 2026-09-28

Owning module: P16
Rollback/recovery notes: downgrade drops approvals and approval_events — every approval decision and its history is
lost, and P17 would have nothing approved to execute. Source items (P08 negatives, P09 ads, P14 recommendations, P15
campaigns) are untouched; re-run "Sync queue" to re-create pending requests, then decide them again.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P16"

revision = "0013_p16"
down_revision = "0012_p15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("source_module", sa.String(8), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=False, index=True),
        sa.Column("change_type", sa.String(48), nullable=False),
        sa.Column("impact", sa.String(16), nullable=False),
        sa.Column("risk", sa.String(16), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("before", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("after", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("payload", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending", index=True),
        sa.Column("requested_by", sa.String(255)),
        sa.Column("decided_by", sa.String(255)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_note", sa.Text()),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("execution_result", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "approval_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("approval_id", sa.Integer(), sa.ForeignKey("approvals.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event", sa.String(24), nullable=False),
        sa.Column("by", sa.String(255)),
        sa.Column("note", sa.Text()),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("approval_events")
    op.drop_table("approvals")
