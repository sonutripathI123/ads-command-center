"""P14 — recommendations (MID §18 contract), ai_runs, ai_evidence. ads_account_id = P04 id (no cross-module FK)."""
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[str] = mapped_column(String(8), nullable=False)          # source module, e.g. P07
    source_ref: Mapped[str] = mapped_column(String(600), nullable=False, index=True)  # source fingerprint
    website_id: Mapped[int | None] = mapped_column(Integer)
    ads_account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, default="account")
    entity_id: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_action: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk: Mapped[str] = mapped_column(String(16), nullable=False)
    assumptions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    link: Mapped[str | None] = mapped_column(String(255))
    # proposed → accepted → done ; proposed → rejected ; proposed → superseded (source no longer reports it)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="proposed")
    decided_by: Mapped[str | None] = mapped_column(String(255))
    decision_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution_result: Mapped[str | None] = mapped_column(Text)


class AIRun(Base):
    __tablename__ = "ai_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ads_account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="action_plan")
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # live | template
    model: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # success | failed
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    output: Mapped[str | None] = mapped_column(Text)   # validated plan JSON
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class AIEvidence(Base):
    """Which recommendations were given to the AI for a run (traceability)."""

    __tablename__ = "ai_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("ai_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_id: Mapped[int] = mapped_column(Integer, nullable=False)
