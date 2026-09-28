"""P05 — warehouse tables. `account_id` is P04's ads_accounts.id (no cross-module FK on purpose).

Entity keys are Google IDs; keywords/ads/search terms are keyed per ad group ("<ad_group_id>~<id or text>")
because criterion/ad IDs and search terms are only unique within an ad group.
Money is stored in micros (1 AUD = 1,000,000 micros) exactly as Google returns it.
"""
from datetime import UTC, date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (UniqueConstraint("account_id", "google_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    google_id: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str | None] = mapped_column(String(32))
    channel_type: Mapped[str | None] = mapped_column(String(64))
    bidding_strategy_type: Mapped[str | None] = mapped_column(String(64))
    budget_micros: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class AdGroup(Base):
    __tablename__ = "ad_groups"
    __table_args__ = (UniqueConstraint("account_id", "google_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    google_id: Mapped[str] = mapped_column(String(32), nullable=False)
    campaign_google_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str | None] = mapped_column(String(32))
    type: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (UniqueConstraint("account_id", "key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    campaign_google_id: Mapped[str] = mapped_column(String(32), nullable=False)
    ad_group_google_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    criterion_id: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    match_type: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str | None] = mapped_column(String(32))
    quality_score: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class SearchTerm(Base):
    __tablename__ = "search_terms"
    __table_args__ = (UniqueConstraint("account_id", "key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(600), nullable=False)
    search_term: Mapped[str] = mapped_column(String(512), nullable=False)
    campaign_google_id: Mapped[str] = mapped_column(String(32), nullable=False)
    ad_group_google_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str | None] = mapped_column(String(32))  # ADDED | EXCLUDED | ADDED_EXCLUDED | NONE
    matched_keyword: Mapped[str | None] = mapped_column(String(512))
    matched_match_type: Mapped[str | None] = mapped_column(String(16))
    first_seen: Mapped[date | None] = mapped_column(Date)
    last_seen: Mapped[date | None] = mapped_column(Date)


class Ad(Base):
    __tablename__ = "ads"
    __table_args__ = (UniqueConstraint("account_id", "key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    campaign_google_id: Mapped[str] = mapped_column(String(32), nullable=False)
    ad_group_google_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ad_id: Mapped[str] = mapped_column(String(32), nullable=False)
    type: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str | None] = mapped_column(String(32))
    final_urls: Mapped[str] = mapped_column(Text, nullable=False, default="[]")    # JSON list
    headlines: Mapped[str] = mapped_column(Text, nullable=False, default="[]")     # JSON list of strings
    descriptions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list of strings
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class MetricsSnapshot(Base):
    """Daily metrics per entity. entity_type: campaign | ad_group | keyword | search_term | ad."""

    __tablename__ = "metrics_snapshots"
    __table_args__ = (
        UniqueConstraint("account_id", "entity_type", "entity_key", "date"),
        Index("ix_metrics_account_type_date", "account_id", "entity_type", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(600), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    impressions: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cost_micros: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    conversions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    conversions_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")  # running|success|partial|failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    counts: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON {step: rows}
    errors: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON {step: message}
    triggered_by_user_id: Mapped[int | None] = mapped_column(Integer)
