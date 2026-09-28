"""P07 — audit_runs, audit_issues. ads_account_id = P04 id, website_id = P03 id (no cross-module FKs).
An issue's `fingerprint` (code + entity) carries dismissals over to later runs."""
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ads_account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    website_id: Mapped[int | None] = mapped_column(Integer)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    counts: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # {"critical": n, ...}
    errors: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # data sources that failed
    triggered_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class AuditIssue(Base):
    __tablename__ = "audit_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    ads_account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(600), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, default="account")
    entity_id: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    link: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")  # open | dismissed
    dismissed_by: Mapped[str | None] = mapped_column(String(255))
    dismiss_note: Mapped[str | None] = mapped_column(Text)
