"""P06: analytics_daily, conversion_events, search_console_daily, conversion_mappings, analytics_sync_runs, bookings

Revision ID: 0008_p06
Revises: 0007_p03
Create Date: 2026-09-28

Owning module: P06
Rollback/recovery notes: downgrade drops all six tables. GA4 / Search Console data is re-synced from Google
("Sync" on the Conversions page). Conversion mappings (lead/booking roles) and imported bookings are lost —
re-import the bookings CSV and re-mark events afterwards.
"""
from alembic import op
import sqlalchemy as sa

module_id = "P06"

revision = "0008_p06"
down_revision = "0007_p03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("website_id", sa.Integer(), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engaged_sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("key_events", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("website_id", "date", "channel"),
    )
    op.create_table(
        "conversion_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("website_id", sa.Integer(), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("event_name", sa.String(128), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("key_events", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("website_id", "date", "event_name"),
    )
    op.create_table(
        "search_console_daily",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("website_id", sa.Integer(), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("query", sa.String(512), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("website_id", "date", "query"),
    )
    op.create_table(
        "conversion_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("website_id", sa.Integer(), nullable=False, index=True),
        sa.Column("event_name", sa.String(128), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("updated_by", sa.String(255)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("website_id", "event_name"),
    )
    op.create_table(
        "analytics_sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("website_id", sa.Integer(), nullable=False, index=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("counts", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("errors", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_system", sa.String(32), nullable=False, server_default="csv"),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("website_id", sa.Integer(), index=True),
        sa.Column("booked_on", sa.Date(), nullable=False, index=True),
        sa.Column("service_date", sa.Date()),
        sa.Column("status", sa.String(32), nullable=False, server_default="confirmed"),
        sa.Column("service_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="AUD"),
        sa.Column("channel", sa.String(64), nullable=False, server_default=""),
        sa.Column("utm_source", sa.String(128), nullable=False, server_default=""),
        sa.Column("utm_medium", sa.String(128), nullable=False, server_default=""),
        sa.Column("utm_campaign", sa.String(255), nullable=False, server_default=""),
        sa.Column("gclid", sa.String(255), nullable=False, server_default=""),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_system", "external_id"),
    )


def downgrade() -> None:
    for t in ("bookings", "analytics_sync_runs", "conversion_mappings", "search_console_daily", "conversion_events", "analytics_daily"):
        op.drop_table(t)
