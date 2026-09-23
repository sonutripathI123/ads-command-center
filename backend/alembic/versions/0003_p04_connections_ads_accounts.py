"""P04: connections and ads_accounts tables

Revision ID: 0003_p04
Revises: 0002_p02
Create Date: 2026-09-23

Owning module: P04
Rollback/recovery notes: downgrade drops ads_accounts then connections. Stored (encrypted) Google
refresh tokens are lost; reconnect via "Connect Google Ads" and re-add accounts. Tokens are NOT revoked
at Google by a downgrade — revoke them in the Google account's security settings if needed.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P04"

revision = "0003_p04"
down_revision = "0002_p02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False, server_default="google_ads"),
        sa.Column("google_email", sa.String(255)),
        sa.Column("refresh_token_enc", sa.Text()),
        sa.Column("scopes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_by_user_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ads_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.String(10), nullable=False),
        sa.Column("descriptive_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("currency_code", sa.String(3)),
        sa.Column("time_zone", sa.String(64)),
        sa.Column("is_manager", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_test_account", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("login_customer_id", sa.String(10)),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("connections.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("added_by_user_id", sa.Integer()),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ads_accounts_customer_id", "ads_accounts", ["customer_id"], unique=True)
    op.create_index("ix_ads_accounts_connection_id", "ads_accounts", ["connection_id"])


def downgrade() -> None:
    op.drop_index("ix_ads_accounts_connection_id", table_name="ads_accounts")
    op.drop_index("ix_ads_accounts_customer_id", table_name="ads_accounts")
    op.drop_table("ads_accounts")
    op.drop_table("connections")
