"""P02 — public interface. Other modules import ONLY from here.

Usage in another module's router:

    from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission

    @router.get("/things")
    def things(user: CurrentUser = Depends(require_permission(Permission.READ))): ...

    @router.post("/things", dependencies=[Depends(verify_origin)])
    def create(user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))): ...
"""
from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.permissions import Permission
from app.modules.p02_auth.service import MODULE_ID, AuthFailed, CurrentUser, resolve
from app.shared.config import get_settings
from app.shared.db import get_db
from app.shared.errors import PermissionDenied

SESSION_COOKIE = "acc_session"

__all__ = ["CurrentUser", "Permission", "SESSION_COOKIE", "get_current_user", "require_permission", "verify_origin"]


def get_current_user(request: Request, db: DbSession = Depends(get_db)) -> CurrentUser:
    user = resolve(db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise AuthFailed("Not signed in", module_id=MODULE_ID)
    return user


def require_permission(perm: Permission) -> Callable[..., CurrentUser]:
    def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has(perm):
            raise PermissionDenied(f"Requires '{perm}' permission", module_id=MODULE_ID, details={"permission": perm})
        return user

    return _dep


def verify_origin(request: Request) -> None:
    """CSRF defence for state-changing requests: a browser-sent Origin must be an allowed frontend origin."""
    origin = request.headers.get("origin")
    if origin is not None and origin not in get_settings().cors_origins:
        raise PermissionDenied("Request origin not allowed", module_id=MODULE_ID, details={"origin": origin})
