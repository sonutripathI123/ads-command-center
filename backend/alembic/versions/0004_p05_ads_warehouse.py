"""P05: Google Ads warehouse tables

Revision ID: 0004_p05
Revises: 0003_p04
Create Date: 2026-09-28

Owning module: P05
Rollback/recovery notes: downgrade drops campaigns, ad_groups, keywords, search_terms, ads,
metrics_snapshots and sync_runs. All of it is a copy of Google Ads data: after re-upgrading, run
`python -m app.modules.p05_ads_sync.cli sync --days 365` to rebuild. Nothing is lost at Google.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P05"

revision = "0004_p05"
down_revision = "0003_p04"
branch_labels = None
depends_on = None


def _ts(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("google_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("status", sa.String(32)), sa.Column("channel_type", sa.String(64)),
        sa.Column("bidding_strategy_type", sa.String(64)), sa.Column("budget_micros", sa.BigInteger()),
        _ts("updated_at"), sa.UniqueConstraint("account_id", "google_id"),
    )
    op.create_table(
        "ad_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("google_id", sa.String(32), nullable=False),
        sa.Column("campaign_google_id", sa.String(32), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("status", sa.String(32)), sa.Column("type", sa.String(64)),
        _ts("updated_at"), sa.UniqueConstraint("account_id", "google_id"),
    )
    op.create_table(
        "keywords",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("campaign_google_id", sa.String(32), nullable=False),
        sa.Column("ad_group_google_id", sa.String(32), nullable=False, index=True),
        sa.Column("criterion_id", sa.String(32), nullable=False),
        sa.Column("text", sa.String(512), nullable=False, server_default=""),
        sa.Column("match_type", sa.String(16)), sa.Column("status", sa.String(32)),
        sa.Column("quality_score", sa.Integer()),
        _ts("updated_at"), sa.UniqueConstraint("account_id", "key"),
    )
    op.create_table(
        "search_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("key", sa.String(600), nullable=False),
        sa.Column("search_term", sa.String(512), nullable=False),
        sa.Column("campaign_google_id", sa.String(32), nullable=False),
        sa.Column("ad_group_google_id", sa.String(32), nullable=False, index=True),
        sa.Column("status", sa.String(32)), sa.Column("matched_keyword", sa.String(512)),
        sa.Column("matched_match_type", sa.String(16)),
        sa.Column("first_seen", sa.Date()), sa.Column("last_seen", sa.Date()),
        sa.UniqueConstraint("account_id", "key"),
    )
    op.create_table(
        "ads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("campaign_google_id", sa.String(32), nullable=False),
        sa.Column("ad_group_google_id", sa.String(32), nullable=False, index=True),
        sa.Column("ad_id", sa.String(32), nullable=False),
        sa.Column("type", sa.String(64)), sa.Column("status", sa.String(32)),
        sa.Column("final_urls", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("headlines", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("descriptions", sa.Text(), nullable=False, server_default="[]"),
        _ts("updated_at"), sa.UniqueConstraint("account_id", "key"),
    )
    op.create_table(
        "metrics_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(16), nullable=False),
        sa.Column("entity_key", sa.String(600), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("impressions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cost_micros", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Float(), nullable=False, server_default="0"),
        sa.Column("conversions_value", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("account_id", "entity_type", "entity_key", "date"),
    )
    op.create_index("ix_metrics_account_type_date", "metrics_snapshots", ["account_id", "entity_type", "date"])
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False, index=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        _ts("started_at"), _ts("finished_at", nullable=True),
        sa.Column("date_from", sa.Date(), nullable=False), sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("counts", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("errors", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("triggered_by_user_id", sa.Integer()),
    )


def downgrade() -> None:
    op.drop_table("sync_runs")
    op.drop_index("ix_metrics_account_type_date", table_name="metrics_snapshots")
    for t in ("metrics_snapshots", "ads", "search_terms", "keywords", "ad_groups", "campaigns"):
        op.drop_table(t)
