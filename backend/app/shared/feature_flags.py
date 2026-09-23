"""SHARED (owner: P00) — feature flag resolution.

Resolution order for a flag:
  1. Flag must be declared in docs/modules.json (unknown keys raise — no typos silently evaluating False).
  2. Declared default.
  3. DB override (table feature_flag_overrides, owned by P00), if present.
  4. If the flag is kill_switch_guarded and ADS_EXECUTION_KILL_SWITCH is true -> False, always.

Public interface: is_enabled, resolve_all, require_enabled
"""
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.shared.config import get_settings
from app.shared.db import Base
from app.shared.errors import FeatureDisabled
from app.shared.registry import load_registry


class FeatureFlagOverride(Base):
    """Table owned by P00. Rows are written only by an authorised admin path (P02/P22, later)."""

    __tablename__ = "feature_flag_overrides"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                                                 onupdate=lambda: datetime.now(UTC))


class UnknownFlagError(KeyError):
    pass


@dataclass(frozen=True)
class FlagState:
    key: str
    module_id: str
    enabled: bool
    source: str  # default | override | kill_switch
    description: str


def _override(db: Session | None, key: str) -> bool | None:
    if db is None:
        return None
    row = db.get(FeatureFlagOverride, key)
    return None if row is None else row.enabled


def resolve(key: str, db: Session | None = None) -> FlagState:
    spec = load_registry().flags.get(key)
    if spec is None:
        raise UnknownFlagError(key)
    enabled, source = spec.default, "default"
    override = _override(db, key)
    if override is not None:
        enabled, source = override, "override"
    if spec.kill_switch_guarded and get_settings().ads_execution_kill_switch:
        enabled, source = False, "kill_switch"
    return FlagState(key=key, module_id=spec.module_id, enabled=enabled, source=source, description=spec.description)


def is_enabled(key: str, db: Session | None = None) -> bool:
    return resolve(key, db).enabled


def resolve_all(db: Session | None = None) -> list[FlagState]:
    return [resolve(k, db) for k in sorted(load_registry().flags)]


def require_enabled(key: str, db: Session | None, *, module_id: str) -> None:
    state = resolve(key, db)
    if not state.enabled:
        raise FeatureDisabled(f"Feature '{key}' is disabled ({state.source})", module_id=module_id,
                              details={"flag": key, "source": state.source})
