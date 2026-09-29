"""P11 — competitors, competitor_observations (facts, each with its source) and competitor_analyses (AI/rule-based
interpretation, stored separately and labelled). account_id = P04 id."""
from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Competitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (UniqueConstraint("account_id", "domain", name="uq_competitor_account_domain"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    brand_terms: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # active | archived
    last_researched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    research_notes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class CompetitorObservation(Base):
    __tablename__ = "competitor_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)       # page | serp | note
    source: Mapped[str] = mapped_column(String(1024), nullable=False)   # URL, or "manual: <query>"
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # page rows replaced by a newer research run → 0
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class CompetitorAnalysis(Base):
    __tablename__ = "competitor_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)       # live | template
    model: Mapped[str | None] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    observation_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
