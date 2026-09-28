"""P20: experiments

Revision ID: 0014_p20
Revises: 0013_p16
Create Date: 2026-09-28

Owning module: P20
Rollback/recovery notes: downgrade drops experiments — every hypothesis, period, stored result and conclusion is lost.
The underlying metrics live in P05 and are untouched, so results can be recomputed by re-creating the experiment.
Linked P16 approval records stay (their payload keeps the old experiment id).
"""
from alembic import op
import sqlalchemy as sa

module_id = "P20"

revision = "0014_p20"
down_revision = "0013_p16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False, server_default=""),
        sa.Column("change_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("entity_type", sa.String(16), nullable=False),
        sa.Column("control_ref", sa.String(128), nullable=False),
        sa.Column("variant_ref", sa.String(128)),
        sa.Column("primary_metric", sa.String(32), nullable=False),
        sa.Column("baseline_start", sa.Date()),
        sa.Column("baseline_end", sa.Date()),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("min_clicks", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft", index=True),
        sa.Column("approval_id", sa.Integer()),
        sa.Column("results", sa.Text()),
        sa.Column("conclusion", sa.Text()),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("experiments")
