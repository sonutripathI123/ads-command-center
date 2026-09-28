"""P21 — load/save versioned rules. A saved account scope replaces the global scope for that account."""
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p21_business_rules.models import BusinessRule, BusinessRuleVersion
from app.modules.p21_business_rules.rules import Rules
from app.shared.errors import ValidationFailed
from app.shared.logging import get_logger

MODULE_ID = "P21"
log = get_logger(MODULE_ID)


def scope_for(account_id: int | None) -> str:
    return "global" if account_id is None else f"account:{account_id}"


@dataclass(frozen=True)
class Current:
    scope: str
    version: int  # 0 = built-in defaults, never saved
    rules: Rules
    updated_at: datetime | None
    updated_by: str | None
    note: str


def _version(db: DbSession, scope: str) -> BusinessRuleVersion | None:
    head = db.get(BusinessRule, scope)
    if head is None:
        return None
    return db.scalar(select(BusinessRuleVersion).where(BusinessRuleVersion.scope == scope,
                                                       BusinessRuleVersion.version == head.current_version))


def current(db: DbSession, scope: str) -> Current:
    v = _version(db, scope)
    if v is None:
        return Current(scope=scope, version=0, rules=Rules(), updated_at=None, updated_by=None, note="built-in defaults")
    return Current(scope=scope, version=v.version, rules=Rules.model_validate_json(v.data), updated_at=v.created_at,
                   updated_by=v.created_by_email, note=v.note)


def effective(db: DbSession, account_id: int | None) -> Rules:
    """The account's own rules if saved for it, otherwise the global rules (otherwise built-in defaults)."""
    if account_id is not None and (v := _version(db, scope_for(account_id))) is not None:
        return Rules.model_validate_json(v.data)
    return current(db, "global").rules


def save(db: DbSession, scope: str, rules: Rules, *, note: str, user_id: int | None, email: str | None) -> Current:
    if not (scope == "global" or (scope.startswith("account:") and scope[8:].isdigit())):
        raise ValidationFailed("Invalid scope", module_id=MODULE_ID)
    head = db.get(BusinessRule, scope)
    prev = _version(db, scope)
    if prev is not None and Rules.model_validate_json(prev.data) == rules:
        return current(db, scope)  # no change → no new version
    nxt = (head.current_version if head else 0) + 1
    db.add(BusinessRuleVersion(scope=scope, version=nxt, data=rules.model_dump_json(), note=note[:2000],
                               created_by_user_id=user_id, created_by_email=email))
    if head is None:
        db.add(BusinessRule(scope=scope, current_version=nxt))
    else:
        head.current_version, head.updated_at = nxt, datetime.now(UTC)
    db.commit()
    log.info("rules_saved", extra={"scope": scope, "version": nxt, "by": email})
    return current(db, scope)


def versions(db: DbSession, scope: str) -> list[BusinessRuleVersion]:
    return list(db.scalars(select(BusinessRuleVersion).where(BusinessRuleVersion.scope == scope)
                           .order_by(BusinessRuleVersion.version.desc())))


def restore(db: DbSession, scope: str, version: int, *, user_id: int | None, email: str | None) -> Current:
    v = db.scalar(select(BusinessRuleVersion).where(BusinessRuleVersion.scope == scope, BusinessRuleVersion.version == version))
    if v is None:
        raise ValidationFailed("Version not found", module_id=MODULE_ID)
    return save(db, scope, Rules.model_validate_json(v.data), note=f"restored v{version}", user_id=user_id, email=email)
