"""P19 — report_runs: a frozen snapshot of each generated report (so a sent report can be reproduced exactly)."""
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class ReportRun(Base):
    __tablename__ = "report_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)     # account | website
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(16), nullable=False)    # daily | weekly | monthly | custom
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
