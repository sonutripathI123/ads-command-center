"""P02 — routes under /api/v1/auth."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth import service
from app.modules.p02_auth.interface import SESSION_COOKIE, get_current_user, require_permission, verify_origin
from app.modules.p02_auth.models import User
from app.modules.p02_auth.permissions import ROLE_PERMISSIONS, Permission
from app.modules.p02_auth.schemas import LoginIn, MeOut, RolesOut, UserCreateIn, UserOut, UserUpdateIn
from app.shared.config import get_settings
from app.shared.db import get_db

router = APIRouter()


def _me(u: service.CurrentUser) -> MeOut:
    return MeOut(id=u.id, email=u.email, name=u.name, role=u.role, permissions=sorted(u.permissions))


def _user(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, name=u.name, role=u.role, execute_enabled=u.execute_enabled,
                   is_active=u.is_active, created_at=u.created_at, last_login_at=u.last_login_at)


@router.post("/login", response_model=MeOut, dependencies=[Depends(verify_origin)])
def login(body: LoginIn, request: Request, response: Response, db: DbSession = Depends(get_db)) -> MeOut:
    token, user = service.login(db, body.email, body.password,
                                ip=request.client.host if request.client else None,
                                user_agent=request.headers.get("user-agent"))
    response.set_cookie(SESSION_COOKIE, token, max_age=int(service.SESSION_TTL.total_seconds()), httponly=True,
                        samesite="lax", secure=get_settings().is_production, path="/")
    return _me(user)


@router.post("/logout", status_code=204, dependencies=[Depends(verify_origin)])
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)) -> Response:
    service.logout(db, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=MeOut)
def me(user: service.CurrentUser = Depends(get_current_user)) -> MeOut:
    return _me(user)


@router.get("/roles", response_model=RolesOut)
def roles(_: service.CurrentUser = Depends(get_current_user)) -> RolesOut:
    return RolesOut(roles={r: sorted(p) for r, p in ROLE_PERMISSIONS.items()})


@router.get("/users", response_model=list[UserOut])
def list_users(db: DbSession = Depends(get_db), _=Depends(require_permission(Permission.ADMIN))) -> list[UserOut]:
    return [_user(u) for u in service.list_users(db)]


@router.post("/users", response_model=UserOut, status_code=201, dependencies=[Depends(verify_origin)])
def create_user(body: UserCreateIn, db: DbSession = Depends(get_db),
                _=Depends(require_permission(Permission.ADMIN))) -> UserOut:
    return _user(service.create_user(db, email=body.email, name=body.name, role=body.role, password=body.password))


@router.patch("/users/{user_id}", response_model=UserOut, dependencies=[Depends(verify_origin)])
def update_user(user_id: int, body: UserUpdateIn, db: DbSession = Depends(get_db),
                actor: service.CurrentUser = Depends(require_permission(Permission.ADMIN))) -> UserOut:
    return _user(service.update_user(db, actor, user_id, role=body.role, is_active=body.is_active, name=body.name))
