"""P15 — campaign_drafts. One row per draft campaign; structure kept as JSON (ad groups, keywords, negatives).
account_id = P04 id, website_id = P03 id, ad drafts referenced by P09 id (no cross-module FKs)."""
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class CampaignDraft(Base):
    __tablename__ = "campaign_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    website_id: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(Text, nullable=False, default="{}")        # JSON: source ad groups, window
    settings: Mapped[str] = mapped_column(Text, nullable=False, default="{}")      # JSON
    ad_groups: Mapped[str] = mapped_column(Text, nullable=False, default="[]")     # JSON list
    unassigned: Mapped[str] = mapped_column(Text, nullable=False, default="[]")    # JSON list of keywords
    negatives: Mapped[str] = mapped_column(Text, nullable=False, default="[]")     # JSON list
    tracking_issues: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")  # draft | approved | archived
    created_by: Mapped[str | None] = mapped_column(String(255))
    approved_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
