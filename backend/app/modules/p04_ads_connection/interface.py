"""P04 — public interface (used by P05 sync and P17 execution).

    from app.modules.p04_ads_connection.interface import active_accounts, open_read_session

    for acc in active_accounts(db):
        s = open_read_session(db, acc.id, http)
        rows = s.search("SELECT campaign.id, campaign.name FROM campaign")
"""
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p04_ads_connection import service
from app.modules.p04_ads_connection.adapters.google_ads import ADS_BASE, GoogleAdsReadClient
from app.modules.p04_ads_connection.models import AdsAccount, Connection
from app.shared.errors import NotFoundError, ValidationFailed

__all__ = ["AccountRef", "ApiCredentials", "ReadSession", "active_accounts", "open_api_credentials", "open_read_session"]


@dataclass(frozen=True)
class AccountRef:
    id: int
    customer_id: str
    descriptive_name: str
    currency_code: str | None
    time_zone: str | None
    login_customer_id: str | None


@dataclass
class ReadSession:
    """A short-lived, read-only session for one account (GAQL SELECT only)."""

    account: AccountRef
    _client: GoogleAdsReadClient
    _token: str

    def search(self, query: str) -> list[dict]:
        return self._client.search(self._token, self.account.customer_id, query,
                                   login_customer_id=self.account.login_customer_id)


@dataclass
class ApiCredentials:
    """Short-lived authenticated access to one account's Google Ads REST API, for P17 (execution) only.
    P04 itself never uses it to change anything — it only hands out the headers and versioned base URL."""

    account: AccountRef
    http: httpx.Client
    base_url: str
    _headers: dict[str, str]

    def headers(self) -> dict[str, str]:
        return dict(self._headers)


def _ref(a: AdsAccount) -> AccountRef:
    return AccountRef(id=a.id, customer_id=a.customer_id, descriptive_name=a.descriptive_name,
                      currency_code=a.currency_code, time_zone=a.time_zone, login_customer_id=a.login_customer_id)


def active_accounts(db: DbSession) -> list[AccountRef]:
    q = (select(AdsAccount).join(Connection, Connection.id == AdsAccount.connection_id)
         .where(AdsAccount.status == "active", AdsAccount.is_manager.is_(False), Connection.status != "revoked"))
    return [_ref(a) for a in db.scalars(q)]


def open_read_session(db: DbSession, account_id: int, http: httpx.Client) -> ReadSession:
    acc = db.get(AdsAccount, account_id)
    if acc is None:
        raise NotFoundError("Ads account not found", module_id=service.MODULE_ID)
    if acc.status != "active":
        raise ValidationFailed("Ads account is disabled", module_id=service.MODULE_ID)
    client = service.make_client(http)
    token = service._access_token(db, client, service.get_connection(db, acc.connection_id))
    return ReadSession(account=_ref(acc), _client=client, _token=token)


def open_api_credentials(db: DbSession, account_id: int, http: httpx.Client) -> ApiCredentials:
    """For P17 only: authenticated headers + versioned base URL for one active account (token is short-lived)."""
    acc = db.get(AdsAccount, account_id)
    if acc is None:
        raise NotFoundError("Ads account not found", module_id=service.MODULE_ID)
    if acc.status != "active":
        raise ValidationFailed("Ads account is disabled", module_id=service.MODULE_ID)
    client = service.make_client(http)
    token = service._access_token(db, client, service.get_connection(db, acc.connection_id))
    ref = _ref(acc)
    return ApiCredentials(account=ref, http=http, base_url=f"{ADS_BASE}/{client.api_version}",
                          _headers=client._headers(token, ref.login_customer_id))
