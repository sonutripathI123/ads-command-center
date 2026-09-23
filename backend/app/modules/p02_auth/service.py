"""P02 — authentication and user-management logic."""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.models import Session, User
from app.modules.p02_auth.permissions import ROLES, Permission, permissions_for
from app.modules.p02_auth.security import (
    DUMMY_HASH, MIN_PASSWORD_LENGTH, hash_password, new_session_token, throttle, token_hash, verify_password,
)
from app.shared.errors import AppError, NotFoundError, PermissionDenied, ValidationFailed
from app.shared.logging import get_logger

MODULE_ID = "P02"
SESSION_TTL = timedelta(hours=12)
log = get_logger(MODULE_ID)


class AuthFailed(AppError):
    status_code = 401
    code = "auth_failed"


class TooManyAttempts(AppError):
    status_code = 429
    code = "too_many_attempts"


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str
    name: str
    role: str
    permissions: frozenset[Permission]

    def has(self, perm: Permission) -> bool:
        return perm in self.permissions


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)  # SQLite returns naive datetimes


def _to_current(u: User) -> CurrentUser:
    return CurrentUser(id=u.id, email=u.email, name=u.name, role=u.role,
                       permissions=permissions_for(u.role, u.execute_enabled))


def normalise_email(email: str) -> str:
    return email.strip().lower()


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationFailed(f"Password must be at least {MIN_PASSWORD_LENGTH} characters", module_id=MODULE_ID)


def login(db: DbSession, email: str, password: str, *, ip: str | None, user_agent: str | None) -> tuple[str, CurrentUser]:
    email = normalise_email(email)
    if throttle.blocked(email):
        raise TooManyAttempts("Too many failed attempts. Try again in 15 minutes.", module_id=MODULE_ID)
    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(password, user.password_hash if user else DUMMY_HASH) and user is not None and user.is_active
    if not ok:
        throttle.fail(email)
        log.warning("login_failed", extra={"email": email, "ip": ip})
        raise AuthFailed("Invalid email or password", module_id=MODULE_ID)
    throttle.reset(email)

    token = new_session_token()
    now = datetime.now(UTC)
    db.add(Session(token_hash=token_hash(token), user_id=user.id, created_at=now, expires_at=now + SESSION_TTL,
                   ip=ip, user_agent=(user_agent or "")[:255]))
    user.last_login_at = now
    db.execute(delete(Session).where(Session.user_id == user.id, Session.expires_at < now))
    db.commit()
    log.info("login_ok", extra={"user_id": user.id})
    return token, _to_current(user)


def resolve(db: DbSession, token: str | None) -> CurrentUser | None:
    if not token:
        return None
    s = db.get(Session, token_hash(token))
    if s is None or _utc(s.expires_at) <= datetime.now(UTC):
        return None
    user = db.get(User, s.user_id)
    return _to_current(user) if user and user.is_active else None


def logout(db: DbSession, token: str | None) -> None:
    if token:
        db.execute(delete(Session).where(Session.token_hash == token_hash(token)))
        db.commit()


# ---- user management (admin) ------------------------------------------------

def list_users(db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


def create_user(db: DbSession, *, email: str, name: str, role: str, password: str) -> User:
    email = normalise_email(email)
    if role not in ROLES:
        raise ValidationFailed(f"Unknown role '{role}'", module_id=MODULE_ID, details={"roles": list(ROLES)})
    validate_password(password)
    if db.scalar(select(User).where(User.email == email)):
        raise ValidationFailed("A user with this email already exists", module_id=MODULE_ID)
    user = User(email=email, name=name.strip(), role=role, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    log.info("user_created", extra={"user_id": user.id, "role": role})
    return user


def _active_admins(db: DbSession) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))) or 0


def update_user(db: DbSession, actor: CurrentUser, user_id: int, *, role: str | None, is_active: bool | None,
                name: str | None) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found", module_id=MODULE_ID)
    if role is not None and role not in ROLES:
        raise ValidationFailed(f"Unknown role '{role}'", module_id=MODULE_ID, details={"roles": list(ROLES)})
    losing_admin = user.role == "admin" and user.is_active and (
        (role is not None and role != "admin") or is_active is False)
    if losing_admin and _active_admins(db) <= 1:
        raise PermissionDenied("Cannot remove the last active admin", module_id=MODULE_ID)
    if user.id == actor.id and is_active is False:
        raise PermissionDenied("You cannot deactivate yourself", module_id=MODULE_ID)
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
        if not is_active:
            db.execute(delete(Session).where(Session.user_id == user.id))
    if name is not None:
        user.name = name.strip()
    db.commit()
    log.info("user_updated", extra={"user_id": user.id, "by": actor.id, "role": user.role, "active": user.is_active})
    return user
