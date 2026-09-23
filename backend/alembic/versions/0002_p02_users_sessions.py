"""P02: users and sessions tables

Revision ID: 0002_p02
Revises: 0001_p00
Create Date: 2026-09-23

Owning module: P02
Rollback/recovery notes: downgrade drops sessions then users — every account and login is lost.
Before downgrading in production, back up both tables (pg_dump -t users -t sessions). Recreate
admins afterwards with `python -m app.modules.p02_auth.cli create-admin`.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P02"

revision = "0002_p02"
down_revision = "0001_p00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column("execute_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(255)),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
