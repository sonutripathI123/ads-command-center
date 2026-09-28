"""P03: websites, crawl_runs, pages, page_signals, landing_page_mappings

Revision ID: 0007_p03
Revises: 0006_p08
Create Date: 2026-09-28

Owning module: P03
Rollback/recovery notes: downgrade drops all five tables. Website records (name, domain, linked ads account,
GA4 / Search Console IDs) are lost and must be re-entered; crawl data is rebuilt with "Scan website".
Export first with GET /api/v1/websites if needed.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P03"

revision = "0007_p03"
down_revision = "0006_p08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "websites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False, unique=True),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("primary_service", sa.String(128), nullable=False, server_default=""),
        sa.Column("location", sa.String(128), nullable=False, server_default=""),
        sa.Column("time_zone", sa.String(64), nullable=False, server_default="Australia/Melbourne"),
        sa.Column("ads_account_id", sa.Integer(), index=True),
        sa.Column("ga4_property_id", sa.String(32)),
        sa.Column("gsc_site_url", sa.String(512)),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("website_id", sa.Integer(), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("pages_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_crawled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(16), nullable=False, server_default=""),
        sa.Column("errors", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("triggered_by_user_id", sa.Integer()),
    )
    op.create_table(
        "pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("website_id", sa.Integer(), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("status_code", sa.Integer()), sa.Column("final_url", sa.String(1024)),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("h1", sa.Text(), nullable=False, server_default=""),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_ms", sa.Float()),
        sa.Column("services", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("locations", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("issues", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("has_form", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_phone", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cta_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_crawl_run_id", sa.Integer()),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("website_id", "url"),
    )
    op.create_table(
        "page_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("crawl_run_id", sa.Integer(), sa.ForeignKey("crawl_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("signals", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "landing_page_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("website_id", sa.Integer(), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ad_key", sa.String(80), nullable=False),
        sa.Column("campaign_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("ad_group_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("final_url", sa.String(1024), nullable=False),
        sa.Column("page_id", sa.Integer()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("website_id", "ad_key", "final_url"),
    )


def downgrade() -> None:
    for t in ("landing_page_mappings", "page_signals", "pages", "crawl_runs", "websites"):
        op.drop_table(t)
