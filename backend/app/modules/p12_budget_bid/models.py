"""P12 — segment_runs (one read-only pull from Google Ads, kept as a snapshot) and segment_findings (what the analysis found)."""
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class SegmentRun(Base):
    __tablename__ = "segment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)          # success | failed
    error: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON: per-dimension tables + budget rows
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class SegmentFinding(Base):
    __tablename__ = "segment_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(16), nullable=False)       # device | day | daypart | location | budget
    segment: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)        # warning | info
    title: Mapped[str] = mapped_column(Text, nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    proposed_action: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(8), nullable=False)       # low | medium
