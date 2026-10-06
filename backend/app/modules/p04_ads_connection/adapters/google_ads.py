"""P04 — READ-ONLY adapter for Google OAuth + Google Ads REST API.

Only these calls exist here: OAuth code exchange / refresh / revoke, userinfo,
customers:listAccessibleCustomers and googleAds:search (GAQL SELECT). There is deliberately no
mutate call — live changes belong to P17 only (enforced by tests/isolation).
"""
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.modules.p24_hardening.interface import request_with_retry

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
ADS_BASE = "https://googleads.googleapis.com"
SCOPES = ("https://www.googleapis.com/auth/adwords", "openid", "email")


class GoogleApiError(Exception):
    def __init__(self, message: str, *, status: int | None = None, reason: str | None = None):
        super().__init__(message)
        self.message, self.status, self.reason = message, status, reason


def _raise_for(r: httpx.Response, what: str) -> None:
    if r.is_success:
        return
    try:
        body = r.json()
    except ValueError:
        body = {}
    err = body.get("error")
    if isinstance(err, dict):  # Google APIs error format
        details = err.get("details") or []
        reason = None
        for d in details:
            for e in d.get("errors", []) or []:
                code = e.get("errorCode") or {}
                reason = reason or next(iter(code.values()), None)
        raise GoogleApiError(f"{what}: {err.get('message', r.text[:200])}", status=r.status_code,
                             reason=reason or err.get("status"))
    # OAuth error format: {"error": "invalid_grant", "error_description": "..."}
    raise GoogleApiError(f"{what}: {body.get('error_description') or err or r.text[:200]}", status=r.status_code,
                         reason=err if isinstance(err, str) else None)


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    scope: str


@dataclass(frozen=True)
class CustomerInfo:
    customer_id: str
    descriptive_name: str
    currency_code: str | None
    time_zone: str | None
    is_manager: bool
    is_test_account: bool
    status: str | None
    login_customer_id: str | None  # manager to send as login-customer-id, if reached through one


class GoogleAdsReadClient:
    def __init__(self, http: httpx.Client, *, client_id: str, client_secret: str, developer_token: str | None,
                 api_version: str):
        self.http = http
        self.client_id, self.client_secret = client_id, client_secret
        self.developer_token = developer_token
        self.api_version = api_version

    # ---- OAuth ----------------------------------------------------------------
    def authorization_url(self, *, redirect_uri: str, state: str) -> str:
        return AUTH_URL + "?" + urlencode({
            "client_id": self.client_id, "redirect_uri": redirect_uri, "response_type": "code",
            "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent",
            "include_granted_scopes": "true", "state": state,
        })

    def exchange_code(self, code: str, *, redirect_uri: str) -> OAuthTokens:
        r = self.http.post(TOKEN_URL, data={"code": code, "client_id": self.client_id,
                                            "client_secret": self.client_secret, "redirect_uri": redirect_uri,
                                            "grant_type": "authorization_code"})
        _raise_for(r, "Google sign-in failed")
        b = r.json()
        return OAuthTokens(access_token=b["access_token"], refresh_token=b.get("refresh_token"), scope=b.get("scope", ""))

    def access_token(self, refresh_token: str) -> str:
        r = request_with_retry(lambda: self.http.post(TOKEN_URL, data={
            "refresh_token": refresh_token, "client_id": self.client_id, "client_secret": self.client_secret, "grant_type": "refresh_token"}))
        _raise_for(r, "Could not refresh Google access")
        return r.json()["access_token"]

    def revoke(self, token: str) -> None:
        r = self.http.post(REVOKE_URL, data={"token": token})
        if r.status_code not in (200, 400):  # 400 = already revoked/invalid
            _raise_for(r, "Could not revoke Google access")

    def user_email(self, access_token: str) -> str | None:
        r = self.http.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        return r.json().get("email") if r.is_success else None

    # ---- Google Ads (read-only) ------------------------------------------------
    def _headers(self, access_token: str, login_customer_id: str | None = None) -> dict[str, str]:
        if not self.developer_token:
            raise GoogleApiError("GOOGLE_ADS_DEVELOPER_TOKEN is not configured", reason="DEVELOPER_TOKEN_MISSING")
        h = {"Authorization": f"Bearer {access_token}", "developer-token": self.developer_token}
        if login_customer_id:
            h["login-customer-id"] = login_customer_id
        return h

    def list_accessible_customers(self, access_token: str) -> list[str]:
        headers = self._headers(access_token)
        r = request_with_retry(lambda: self.http.get(f"{ADS_BASE}/{self.api_version}/customers:listAccessibleCustomers", headers=headers))
        _raise_for(r, "Google Ads: list accounts failed")
        return [rn.split("/")[-1] for rn in r.json().get("resourceNames", [])]

    def search(self, access_token: str, customer_id: str, query: str, *,
               login_customer_id: str | None = None) -> list[dict]:
        """GAQL SELECT only. Follows pagination."""
        if not query.lstrip().upper().startswith("SELECT"):
            raise ValueError("Only GAQL SELECT queries are allowed")
        rows, page_token = [], None
        while True:
            body = {"query": query} | ({"pageToken": page_token} if page_token else {})
            headers = self._headers(access_token, login_customer_id)
            r = request_with_retry(lambda: self.http.post(f"{ADS_BASE}/{self.api_version}/customers/{customer_id}/googleAds:search",
                                                          headers=headers, json=body))
            _raise_for(r, f"Google Ads: query on {customer_id} failed")
            b = r.json()
            rows += b.get("results", [])
            page_token = b.get("nextPageToken")
            if not page_token:
                return rows

    def customer_info(self, access_token: str, customer_id: str, *, login_customer_id: str | None = None) -> CustomerInfo:
        rows = self.search(access_token, customer_id,
                           "SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.time_zone, "
                           "customer.manager, customer.test_account, customer.status FROM customer LIMIT 1",
                           login_customer_id=login_customer_id)
        c = rows[0]["customer"] if rows else {}
        return CustomerInfo(customer_id=str(c.get("id", customer_id)), descriptive_name=c.get("descriptiveName", ""),
                            currency_code=c.get("currencyCode"), time_zone=c.get("timeZone"),
                            is_manager=bool(c.get("manager")), is_test_account=bool(c.get("testAccount")),
                            status=c.get("status"), login_customer_id=login_customer_id)

    def child_accounts(self, access_token: str, manager_id: str) -> list[CustomerInfo]:
        rows = self.search(access_token, manager_id,
                           "SELECT customer_client.id, customer_client.descriptive_name, customer_client.currency_code, "
                           "customer_client.time_zone, customer_client.manager, customer_client.test_account, "
                           "customer_client.status, customer_client.level FROM customer_client "
                           "WHERE customer_client.level = 1",
                           login_customer_id=manager_id)
        out = []
        for row in rows:
            c = row["customerClient"]
            out.append(CustomerInfo(customer_id=str(c["id"]), descriptive_name=c.get("descriptiveName", ""),
                                    currency_code=c.get("currencyCode"), time_zone=c.get("timeZone"),
                                    is_manager=bool(c.get("manager")), is_test_account=bool(c.get("testAccount")),
                                    status=c.get("status"), login_customer_id=manager_id))
        return out
