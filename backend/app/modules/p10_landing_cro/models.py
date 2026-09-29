"""P10 — landing_page_checks (one row per ad landing URL per check run), cro_findings, implementation_briefs.
account_id = P04 id. `context` = ads/keywords/spend (from P05) that point to the URL at check time."""
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class LandingPageCheck(Base):
    __tablename__ = "landing_page_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    run_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # groups the URLs checked together
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    final_url: Mapped[str | None] = mapped_column(String(1024))
    status_code: Mapped[int | None] = mapped_column(Integer)
    elapsed_ms: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(Text)
    signals: Mapped[str | None] = mapped_column(Text)            # CroSignals JSON
    context: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checked_by: Mapped[str | None] = mapped_column(String(255))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class CroFinding(Base):
    __tablename__ = "cro_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("landing_page_checks.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recommendation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class ImplementationBrief(Base):
    __tablename__ = "implementation_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("landing_page_checks.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)   # live | template
    model: Mapped[str | None] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text, nullable=False)       # Brief JSON
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
