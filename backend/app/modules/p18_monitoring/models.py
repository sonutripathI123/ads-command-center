"""P18 — alerts (one open alert per account + code, auto-resolved when the condition clears) and monitor_checks (runs)."""
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    action: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    link: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)  # open | acknowledged | resolved
    occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    acknowledged_by: Mapped[str | None] = mapped_column(String(255))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(255))  # "auto" when the condition cleared


class MonitorCheck(Base):
    __tablename__ = "monitor_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(16), nullable=False)   # manual | scheduled
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")  # running | success | failed
    signals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    run_by: Mapped[str | None] = mapped_column(String(255))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
