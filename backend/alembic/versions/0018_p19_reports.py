"""P19: report_runs

Revision ID: 0018_p19
Revises: 0017_p18
Create Date: 2026-09-29

Owning module: P19
Rollback/recovery notes: downgrade drops every stored report snapshot. Reports can be regenerated for the same periods,
but they will reflect the data at regeneration time, not what was originally sent. Download CSV/PDF copies first.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P19"

revision = "0018_p19"
down_revision = "0017_p18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=False, index=True),
        sa.Column("period", sa.String(16), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("report_runs")
