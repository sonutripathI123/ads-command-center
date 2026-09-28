"""P06 — tables. website_id = P03 websites.id (no cross-module FK).

Three kinds of numbers are kept apart on purpose (MID §11 P06):
  observed  — GA4 / Search Console (analytics_daily, conversion_events, search_console_daily)
  attributed — Google Ads conversions (read from P05, not stored here)
  confirmed — real bookings from the booking system (bookings)
Bookings store no customer names, emails or phone numbers.
"""
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class AnalyticsDaily(Base):
    __tablename__ = "analytics_daily"
    __table_args__ = (UniqueConstraint("website_id", "date", "channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engaged_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    key_events: Mapped[float] = mapped_column(Float, nullable=False, default=0)


class ConversionEvent(Base):
    __tablename__ = "conversion_events"
    __table_args__ = (UniqueConstraint("website_id", "date", "event_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    key_events: Mapped[float] = mapped_column(Float, nullable=False, default=0)


class SearchConsoleDaily(Base):
    __tablename__ = "search_console_daily"
    __table_args__ = (UniqueConstraint("website_id", "date", "query"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    query: Mapped[str] = mapped_column(String(512), nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[float] = mapped_column(Float, nullable=False, default=0)


class ConversionMapping(Base):
    """What a GA4 event means for the business: lead | booking | micro | ignore."""

    __tablename__ = "conversion_mappings"
    __table_args__ = (UniqueConstraint("website_id", "event_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class AnalyticsSyncRun(Base):
    __tablename__ = "analytics_sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    counts: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    errors: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class Booking(Base):
    """A confirmed booking (from CSV import now; Driver App adapter later). No personal data."""

    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("source_system", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_system: Mapped[str] = mapped_column(String(32), nullable=False, default="csv")
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    website_id: Mapped[int | None] = mapped_column(Integer, index=True)
    booked_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    service_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="confirmed")
    service_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AUD")
    channel: Mapped[str] = mapped_column(String(64), nullable=False, default="")  # as recorded: google ads, phone, …
    utm_source: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    utm_medium: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    utm_campaign: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    gclid: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
