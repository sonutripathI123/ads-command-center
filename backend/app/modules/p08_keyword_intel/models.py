"""P08 — tables. `account_id` = P04 ads_accounts.id. Review decisions (status) survive re-analysis."""
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class SearchTermClassification(Base):
    __tablename__ = "search_term_classifications"
    __table_args__ = (UniqueConstraint("account_id", "term"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    term: Mapped[str] = mapped_column(String(512), nullable=False)
    intent: Mapped[str] = mapped_column(String(32), nullable=False)
    business_value: Mapped[str] = mapped_column(String(16), nullable=False)
    reasons: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    rules_version_note: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class NegativeKeywordCandidate(Base):
    __tablename__ = "negative_keyword_candidates"
    __table_args__ = (UniqueConstraint("account_id", "text", "match_type", "campaign_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    text: Mapped[str] = mapped_column(String(512), nullable=False)
    match_type: Mapped[str] = mapped_column(String(8), nullable=False)
    campaign_key: Mapped[str] = mapped_column(String(32), nullable=False, default="")  # "" = account level
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    term_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    examples: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    window_from: Mapped[date] = mapped_column(Date, nullable=False)
    window_to: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="proposed")  # proposed|accepted|rejected|stale
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class KeywordCandidate(Base):
    """Search terms that converted but are not keywords yet (expansion ideas)."""

    __tablename__ = "keyword_candidates"
    __table_args__ = (UniqueConstraint("account_id", "text", "ad_group_google_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    text: Mapped[str] = mapped_column(String(512), nullable=False)
    suggested_match_type: Mapped[str] = mapped_column(String(8), nullable=False, default="PHRASE")
    campaign_google_id: Mapped[str] = mapped_column(String(32), nullable=False)
    ad_group_google_id: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="proposed")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
