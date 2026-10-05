"""P17 — executions: one row per validate / execute / rollback attempt (append-only history)."""
from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (Index("uq_executions_one_live_execute", "approval_id", unique=True,
                            sqlite_where=text("mode = 'execute' AND status IN ('pending', 'executed', 'unknown', 'rolling_back')"),
                            postgresql_where=text("mode = 'execute' AND status IN ('pending', 'executed', 'unknown', 'rolling_back')")),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    approval_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)       # validate | execute | rollback
    status: Mapped[str] = mapped_column(String(16), nullable=False)     # validated | executed | failed | rolled_back
    change_type: Mapped[str] = mapped_column(String(48), nullable=False)
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="[]")            # JSON: request bodies (no secrets)
    response: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    resource_names: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON: what Google created (for rollback)
    rollback_of: Mapped[int | None] = mapped_column(Integer)
    executed_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
