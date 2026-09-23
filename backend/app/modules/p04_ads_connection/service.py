"""P04 — connection lifecycle: OAuth connect, account discovery, add/disable accounts, health checks."""
import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p04_ads_connection.adapters.google_ads import CustomerInfo, GoogleAdsReadClient, GoogleApiError
from app.modules.p04_ads_connection.config import get_p04_settings
from app.modules.p04_ads_connection.crypto import decrypt, encrypt
from app.modules.p04_ads_connection.models import AdsAccount, Connection
from app.shared.config import get_settings
from app.shared.errors import AppError, NotFoundError, ValidationFailed
from app.shared.logging import get_logger

MODULE_ID = "P04"
STATE_TTL_SECONDS = 600
log = get_logger(MODULE_ID)


class NotConfigured(AppError):
    status_code = 409
    code = "not_configured"


class UpstreamError(AppError):
    status_code = 502
    code = "google_api_error"


def digits(customer_id: str | None) -> str:
    return "".join(c for c in (customer_id or "") if c.isdigit())


def make_client(http: httpx.Client) -> GoogleAdsReadClient:
    s = get_settings()
    if not s.google_oauth_client_id or not s.google_oauth_client_secret:
        raise NotConfigured("Google OAuth client is not configured (GOOGLE_OAUTH_CLIENT_ID/SECRET in backend/.env)",
                            module_id=MODULE_ID)
    return GoogleAdsReadClient(
        http, client_id=s.google_oauth_client_id, client_secret=s.google_oauth_client_secret.get_secret_value(),
        developer_token=s.google_ads_developer_token.get_secret_value() if s.google_ads_developer_token else None,
        api_version=get_p04_settings().google_ads_api_version)


def _upstream(e: GoogleApiError) -> UpstreamError:
    return UpstreamError(e.message, module_id=MODULE_ID, details={"reason": e.reason, "status": e.status})


# ---- OAuth state (HMAC-signed, bound to the browser by a nonce cookie) ---------

def _sign(payload: str) -> str:
    key = get_settings().app_secret_key.get_secret_value().encode()
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def new_oauth_state(user_id: int) -> tuple[str, str]:
    nonce = secrets.token_urlsafe(16)
    payload = f"{user_id}.{nonce}.{int(time.time())}"
    return f"{payload}.{_sign(payload)}", nonce


def verify_oauth_state(state: str, cookie_nonce: str | None, user_id: int) -> None:
    try:
        uid, nonce, ts, sig = state.split(".")
    except ValueError:
        raise ValidationFailed("Invalid OAuth state", module_id=MODULE_ID) from None
    ok = (hmac.compare_digest(sig, _sign(f"{uid}.{nonce}.{ts}")) and cookie_nonce is not None
          and hmac.compare_digest(nonce, cookie_nonce) and uid == str(user_id)
          and time.time() - int(ts) <= STATE_TTL_SECONDS)
    if not ok:
        raise ValidationFailed("OAuth state is invalid or expired — start the connection again", module_id=MODULE_ID)


def authorization_url(client: GoogleAdsReadClient, state: str) -> str:
    return client.authorization_url(redirect_uri=get_p04_settings().google_ads_oauth_redirect_uri, state=state)


def complete_oauth(db: DbSession, client: GoogleAdsReadClient, *, code: str, user_id: int) -> Connection:
    try:
        tokens = client.exchange_code(code, redirect_uri=get_p04_settings().google_ads_oauth_redirect_uri)
    except GoogleApiError as e:
        raise _upstream(e) from e
    if not tokens.refresh_token:
        raise ValidationFailed("Google did not return a refresh token. Remove the app's access in your Google "
                               "account and connect again.", module_id=MODULE_ID)
    if "adwords" not in tokens.scope:
        raise ValidationFailed("Google Ads permission was not granted", module_id=MODULE_ID)
    email = client.user_email(tokens.access_token)
    conn = Connection(provider="google_ads", google_email=email, refresh_token_enc=encrypt(tokens.refresh_token),
                      scopes=tokens.scope, status="active", created_by_user_id=user_id,
                      last_checked_at=datetime.now(UTC))
    db.add(conn)
    db.commit()
    log.info("connection_created", extra={"connection_id": conn.id, "google_email": email})
    return conn


# ---- connections -----------------------------------------------------------------

def get_connection(db: DbSession, connection_id: int) -> Connection:
    conn = db.get(Connection, connection_id)
    if conn is None:
        raise NotFoundError("Connection not found", module_id=MODULE_ID)
    return conn


def _access_token(db: DbSession, client: GoogleAdsReadClient, conn: Connection) -> str:
    if conn.status == "revoked" or not conn.refresh_token_enc:
        raise ValidationFailed("This connection was disconnected", module_id=MODULE_ID)
    try:
        token = client.access_token(decrypt(conn.refresh_token_enc))
    except GoogleApiError as e:
        conn.status, conn.last_error, conn.last_checked_at = "error", e.message, datetime.now(UTC)
        db.commit()
        raise _upstream(e) from e
    return token


def check_connection(db: DbSession, client: GoogleAdsReadClient, conn: Connection) -> tuple[Connection, list[str]]:
    token = _access_token(db, client, conn)
    try:
        ids = client.list_accessible_customers(token)
    except GoogleApiError as e:
        conn.status, conn.last_error = "error", e.message
        conn.last_checked_at = datetime.now(UTC)
        db.commit()
        raise _upstream(e) from e
    conn.status, conn.last_error, conn.last_checked_at = "active", None, datetime.now(UTC)
    db.commit()
    return conn, ids


def disconnect(db: DbSession, client: GoogleAdsReadClient, conn: Connection) -> Connection:
    if conn.refresh_token_enc:
        try:
            client.revoke(decrypt(conn.refresh_token_enc))
        except GoogleApiError as e:
            log.warning("revoke_failed", extra={"connection_id": conn.id, "error": e.message})
    conn.refresh_token_enc, conn.status = None, "revoked"
    for acc in db.scalars(select(AdsAccount).where(AdsAccount.connection_id == conn.id)):
        acc.status = "disabled"
    db.commit()
    log.info("connection_revoked", extra={"connection_id": conn.id})
    return conn


def discover(db: DbSession, client: GoogleAdsReadClient, conn: Connection) -> list[CustomerInfo]:
    """Accounts this Google login can read: directly accessible ones, plus level-1 children of managers."""
    token = _access_token(db, client, conn)
    found: dict[str, CustomerInfo] = {}
    errors: list[str] = []
    try:
        ids = client.list_accessible_customers(token)
    except GoogleApiError as e:
        raise _upstream(e) from e
    for cid in ids:
        try:
            info = client.customer_info(token, cid)
        except GoogleApiError as e:
            errors.append(f"{cid}: {e.message}")
            continue
        found.setdefault(info.customer_id, info)
        if info.is_manager:
            try:
                for child in client.child_accounts(token, info.customer_id):
                    found.setdefault(child.customer_id, child)
            except GoogleApiError as e:
                errors.append(f"{cid} children: {e.message}")
    if not found and errors:
        raise UpstreamError("Could not read any account", module_id=MODULE_ID, details={"errors": errors})
    return sorted(found.values(), key=lambda c: (not c.is_manager, c.descriptive_name.lower()))


# ---- accounts --------------------------------------------------------------------

def list_accounts(db: DbSession) -> list[AdsAccount]:
    return list(db.scalars(select(AdsAccount).order_by(AdsAccount.descriptive_name)))


def add_account(db: DbSession, client: GoogleAdsReadClient, *, connection_id: int, customer_id: str,
                login_customer_id: str | None, user_id: int) -> AdsAccount:
    conn = get_connection(db, connection_id)
    cid, login = digits(customer_id), digits(login_customer_id) or None
    if len(cid) != 10:
        raise ValidationFailed("Customer ID must have 10 digits", module_id=MODULE_ID)
    token = _access_token(db, client, conn)
    try:
        info = client.customer_info(token, cid, login_customer_id=login)
    except GoogleApiError as e:
        raise _upstream(e) from e
    acc = db.scalar(select(AdsAccount).where(AdsAccount.customer_id == cid))
    if acc is None:
        acc = AdsAccount(customer_id=cid, added_by_user_id=user_id)
        db.add(acc)
    acc.descriptive_name, acc.currency_code, acc.time_zone = info.descriptive_name, info.currency_code, info.time_zone
    acc.is_manager, acc.is_test_account = info.is_manager, info.is_test_account
    acc.login_customer_id, acc.connection_id, acc.status = login, conn.id, "active"
    db.commit()
    log.info("account_added", extra={"customer_id": cid, "connection_id": conn.id})
    return acc


def set_account_status(db: DbSession, account_id: int, status: str) -> AdsAccount:
    if status not in ("active", "disabled"):
        raise ValidationFailed("status must be active or disabled", module_id=MODULE_ID)
    acc = db.get(AdsAccount, account_id)
    if acc is None:
        raise NotFoundError("Ads account not found", module_id=MODULE_ID)
    acc.status = status
    db.commit()
    return acc
