"""P03 — tables: websites, crawl_runs, pages (latest snapshot per URL), page_signals (per-crawl history),
landing_page_mappings (ad final URLs → crawled pages). `ads_account_id` = P04 ads_accounts.id (no FK)."""
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Website(Base):
    __tablename__ = "websites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)  # normalised host, e.g. example.com.au
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)             # https://www.example.com.au
    primary_service: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    time_zone: Mapped[str] = mapped_column(String(64), nullable=False, default="Australia/Melbourne")
    ads_account_id: Mapped[int | None] = mapped_column(Integer, index=True)
    ga4_property_id: Mapped[str | None] = mapped_column(String(32))
    gsc_site_url: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # active | archived
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")  # running|success|partial|failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    pages_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_crawled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="")  # sitemap | links
    errors: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    triggered_by_user_id: Mapped[int | None] = mapped_column(Integer)


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("website_id", "url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    final_url: Mapped[str | None] = mapped_column(String(1024))
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    h1: Mapped[str] = mapped_column(Text, nullable=False, default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_ms: Mapped[float | None] = mapped_column(Float)
    services: Mapped[str] = mapped_column(Text, nullable=False, default="[]")   # JSON list (P21 services found)
    locations: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    issues: Mapped[str] = mapped_column(Text, nullable=False, default="[]")     # JSON list of issue codes
    has_form: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_phone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cta_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_crawl_run_id: Mapped[int | None] = mapped_column(Integer)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PageSignal(Base):
    """Full extraction for one page in one crawl (history)."""

    __tablename__ = "page_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True)
    crawl_run_id: Mapped[int] = mapped_column(ForeignKey("crawl_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    signals: Mapped[str] = mapped_column(Text, nullable=False)  # JSON (see extract.PageSignals)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class LandingPageMapping(Base):
    """Which crawled page each ad's final URL points at (for relevance/CRO in P10)."""

    __tablename__ = "landing_page_mappings"
    __table_args__ = (UniqueConstraint("website_id", "ad_key", "final_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True)
    ad_key: Mapped[str] = mapped_column(String(80), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    ad_group_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    final_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    page_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ok | broken | not_crawled | other_domain
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
