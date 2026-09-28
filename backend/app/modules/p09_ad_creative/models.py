"""P09 — ad_drafts, claim_checks. account_id = P04 ads account id (no cross-module FK). Drafts never go live here."""
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class AdDraft(Base):
    __tablename__ = "ad_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    ad_group_google_id: Mapped[str | None] = mapped_column(String(32))
    ad_group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    final_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    keywords: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    usps: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    headlines: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    descriptions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    path1: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    path2: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # live | template | manual
    model: Mapped[str | None] = mapped_column(String(64))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    strength: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")  # draft | approved | rejected
    created_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class ClaimCheck(Base):
    __tablename__ = "claim_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("ad_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(16), nullable=False)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
