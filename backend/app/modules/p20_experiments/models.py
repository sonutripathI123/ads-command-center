"""P20 — experiments. account_id = P04 id; control_ref / variant_ref are P05 entity keys (campaign/ad group google_id, ad key)."""
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    change_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kind: Mapped[str] = mapped_column(String(16), nullable=False)           # a_b | before_after
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)    # campaign | ad_group | ad
    control_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    variant_ref: Mapped[str | None] = mapped_column(String(128))            # a_b only
    primary_metric: Mapped[str] = mapped_column(String(32), nullable=False)
    baseline_start: Mapped[date | None] = mapped_column(Date)               # before_after only
    baseline_end: Mapped[date | None] = mapped_column(Date)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    min_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    # draft → pending_approval → running → completed ; any open state → cancelled
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", index=True)
    approval_id: Mapped[int | None] = mapped_column(Integer)
    results: Mapped[str | None] = mapped_column(Text)
    conclusion: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
