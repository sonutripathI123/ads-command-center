"""P04 — routes under /api/v1/ads-connection. Read-only toward Google Ads."""
from collections.abc import Iterator
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import (
    CurrentUser, Permission, get_current_user, require_permission, verify_origin,
)
from app.modules.p04_ads_connection import service
from app.modules.p04_ads_connection.config import get_p04_settings
from app.modules.p04_ads_connection.models import AdsAccount, Connection
from app.modules.p04_ads_connection.schemas import (
    AccountOut, AccountStatusIn, AddAccountIn, CheckOut, ConnectionOut, DiscoveredOut, StatusOut,
)
from app.shared.config import get_settings
from app.shared.db import get_db
from app.shared.errors import AppError, PermissionDenied

router = APIRouter()
NONCE_COOKIE = "p04_oauth_nonce"
COOKIE_PATH = "/api/v1/ads-connection"


def get_http() -> Iterator[httpx.Client]:
    with httpx.Client(timeout=30) as client:
        yield client


def _conn(c: Connection) -> ConnectionOut:
    return ConnectionOut(id=c.id, google_email=c.google_email, status=c.status, last_checked_at=c.last_checked_at,
                         last_error=c.last_error, created_at=c.created_at)


def _acc(a: AdsAccount) -> AccountOut:
    return AccountOut(id=a.id, customer_id=a.customer_id, descriptive_name=a.descriptive_name,
                      currency_code=a.currency_code, time_zone=a.time_zone, is_manager=a.is_manager,
                      is_test_account=a.is_test_account, login_customer_id=a.login_customer_id,
                      connection_id=a.connection_id, status=a.status, added_at=a.added_at)


def _frontend(query: dict[str, str]) -> RedirectResponse:
    return RedirectResponse(f"{get_p04_settings().frontend_url}/ads-accounts?{urlencode(query)}", status_code=303)


@router.get("/status", response_model=StatusOut)
def status(db: DbSession = Depends(get_db), _: CurrentUser = Depends(require_permission(Permission.READ))) -> StatusOut:
    s, p = get_settings(), get_p04_settings()
    conns = db.query(Connection).order_by(Connection.id).all()
    return StatusOut(oauth_client_configured=bool(s.google_oauth_client_id and s.google_oauth_client_secret),
                     developer_token_configured=bool(s.google_ads_developer_token),
                     api_version=p.google_ads_api_version, redirect_uri=p.google_ads_oauth_redirect_uri,
                     connections=[_conn(c) for c in conns], accounts=[_acc(a) for a in service.list_accounts(db)])


@router.get("/oauth/start")
def oauth_start(http: httpx.Client = Depends(get_http),
                user: CurrentUser = Depends(require_permission(Permission.ADMIN))) -> RedirectResponse:
    state, nonce = service.new_oauth_state(user.id)
    resp = RedirectResponse(service.authorization_url(service.make_client(http), state), status_code=303)
    resp.set_cookie(NONCE_COOKIE, nonce, max_age=service.STATE_TTL_SECONDS, httponly=True, samesite="lax",
                    secure=get_settings().is_production, path=COOKIE_PATH)
    return resp


@router.get("/oauth/callback")
def oauth_callback(request: Request, db: DbSession = Depends(get_db), http: httpx.Client = Depends(get_http),
                   user: CurrentUser = Depends(get_current_user)) -> RedirectResponse:
    params = request.query_params
    try:
        if params.get("error"):
            return _frontend({"error": f"Google: {params['error']}"})
        if not user.has(Permission.ADMIN):
            raise PermissionDenied("Only admins can connect Google Ads", module_id=service.MODULE_ID)
        service.verify_oauth_state(params.get("state", ""), request.cookies.get(NONCE_COOKIE), user.id)
        conn = service.complete_oauth(db, service.make_client(http), code=params.get("code", ""), user_id=user.id)
        resp = _frontend({"connected": str(conn.id)})
    except AppError as e:
        resp = _frontend({"error": e.message[:300]})
    resp.delete_cookie(NONCE_COOKIE, path=COOKIE_PATH)
    return resp


@router.post("/connections/{connection_id}/check", response_model=CheckOut, dependencies=[Depends(verify_origin)])
def check(connection_id: int, db: DbSession = Depends(get_db), http: httpx.Client = Depends(get_http),
          _: CurrentUser = Depends(require_permission(Permission.ADMIN))) -> CheckOut:
    conn, ids = service.check_connection(db, service.make_client(http), service.get_connection(db, connection_id))
    return CheckOut(connection=_conn(conn), accessible_customer_ids=ids)


@router.post("/connections/{connection_id}/disconnect", response_model=ConnectionOut, dependencies=[Depends(verify_origin)])
def disconnect(connection_id: int, db: DbSession = Depends(get_db), http: httpx.Client = Depends(get_http),
               _: CurrentUser = Depends(require_permission(Permission.ADMIN))) -> ConnectionOut:
    return _conn(service.disconnect(db, service.make_client(http), service.get_connection(db, connection_id)))


@router.get("/connections/{connection_id}/discover", response_model=list[DiscoveredOut])
def discover(connection_id: int, db: DbSession = Depends(get_db), http: httpx.Client = Depends(get_http),
             _: CurrentUser = Depends(require_permission(Permission.ADMIN))) -> list[DiscoveredOut]:
    added = {a.customer_id for a in service.list_accounts(db)}
    found = service.discover(db, service.make_client(http), service.get_connection(db, connection_id))
    return [DiscoveredOut(**c.__dict__, already_added=c.customer_id in added) for c in found]


@router.post("/accounts", response_model=AccountOut, status_code=201, dependencies=[Depends(verify_origin)])
def add_account(body: AddAccountIn, db: DbSession = Depends(get_db), http: httpx.Client = Depends(get_http),
                user: CurrentUser = Depends(require_permission(Permission.ADMIN))) -> AccountOut:
    return _acc(service.add_account(db, service.make_client(http), connection_id=body.connection_id,
                                    customer_id=body.customer_id, login_customer_id=body.login_customer_id,
                                    user_id=user.id))


@router.patch("/accounts/{account_id}", response_model=AccountOut, dependencies=[Depends(verify_origin)])
def set_status(account_id: int, body: AccountStatusIn, db: DbSession = Depends(get_db),
               _: CurrentUser = Depends(require_permission(Permission.ADMIN))) -> AccountOut:
    return _acc(service.set_account_status(db, account_id, body.status))
