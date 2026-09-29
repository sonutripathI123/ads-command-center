"""P22: audit_logs

Revision ID: 0019_p22
Revises: 0018_p19
Create Date: 2026-09-29

Owning module: P22
Rollback/recovery notes: downgrade drops the whole audit trail — every recorded before/after change disappears.
The log is append-only by design (no edit/delete anywhere in the API); only a migration downgrade can remove rows.
Export via GET /api/v1/security/audit-logs first if the history is needed.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P22"

revision = "0019_p22"
down_revision = "0018_p19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("module_id", sa.String(8), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(255)),
        sa.Column("actor_role", sa.String(16)),
        sa.Column("entity_type", sa.String(64)),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("before", sa.Text(), nullable=False),
        sa.Column("after", sa.Text(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("request_id", sa.String(64)),
        sa.Column("ip", sa.String(64)),
    )
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_module_action", "audit_logs", ["module_id", "action"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_module_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_table("audit_logs")
