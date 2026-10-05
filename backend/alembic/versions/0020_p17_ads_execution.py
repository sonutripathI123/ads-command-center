"""P17: executions

Revision ID: 0020_p17
Revises: 0019_p22
Create Date: 2026-10-05

Owning module: P17
Rollback/recovery notes: downgrade drops the execution history (what was validated/executed/rolled back, and the Google
resource names needed to undo an execution). Google Ads itself is NOT touched by a downgrade — anything already created
there stays; export the table first if you may need to roll an execution back later.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P17"

revision = "0020_p17"
down_revision = "0019_p22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("approval_id", sa.Integer(), nullable=False, index=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("change_type", sa.String(48), nullable=False),
        sa.Column("plan_hash", sa.String(64), nullable=False, index=True),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("response", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("resource_names", sa.Text(), nullable=False),
        sa.Column("rollback_of", sa.Integer()),
        sa.Column("executed_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_executions_one_live_execute", "executions", ["approval_id"], unique=True,
                    sqlite_where=sa.text("mode = 'execute' AND status IN ('pending', 'executed', 'unknown', 'rolling_back')"), postgresql_where=sa.text("mode = 'execute' AND status IN ('pending', 'executed', 'unknown', 'rolling_back')"))


def downgrade() -> None:
    op.drop_index("uq_executions_one_live_execute", table_name="executions")
    op.drop_table("executions")
