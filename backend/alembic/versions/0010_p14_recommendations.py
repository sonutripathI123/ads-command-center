"""P14: recommendations, ai_runs, ai_evidence

Revision ID: 0010_p14
Revises: 0009_p07
Create Date: 2026-09-28

Owning module: P14
Rollback/recovery notes: downgrade drops all three tables. Recommendations can be rebuilt with "Refresh from
audit", but decisions (accepted / rejected / done, who, notes) and past AI plans are lost.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P14"

revision = "0010_p14"
down_revision = "0009_p07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("module_id", sa.String(8), nullable=False),
        sa.Column("source_ref", sa.String(600), nullable=False, index=True),
        sa.Column("website_id", sa.Integer()),
        sa.Column("ads_account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("entity_type", sa.String(32), nullable=False, server_default="account"),
        sa.Column("entity_id", sa.String(512), nullable=False, server_default=""),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("proposed_action", sa.Text(), nullable=False),
        sa.Column("expected_impact", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("risk", sa.String(16), nullable=False),
        sa.Column("assumptions", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("link", sa.String(255)),
        sa.Column("status", sa.String(16), nullable=False, server_default="proposed"),
        sa.Column("decided_by", sa.String(255)),
        sa.Column("decision_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("execution_result", sa.Text()),
    )
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ads_account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("kind", sa.String(32), nullable=False, server_default="action_plan"),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("model", sa.String(64)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("output", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("created_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ai_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("ai_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("recommendation_id", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    for t in ("ai_evidence", "ai_runs", "recommendations"):
        op.drop_table(t)
