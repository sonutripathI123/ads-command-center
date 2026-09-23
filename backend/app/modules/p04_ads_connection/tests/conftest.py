"""P04 test fixtures: a fake Google (OAuth + Ads REST) behind httpx.MockTransport."""
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p04_ads_connection.models import AdsAccount, Connection
from app.shared.db import Base, get_engine, session_scope
from app.shared.errors import AppError

REFRESH = "1//fake-refresh-token-SECRET"

# Test users are injected through P02's public interface (dependency override), not P02 internals.
_ROLE_PERMS = {
    "viewer": {Permission.READ},
    "analyst": {Permission.READ, Permission.RECOMMEND},
    "approver": {Permission.READ, Permission.RECOMMEND, Permission.APPROVE},
    "admin": {Permission.READ, Permission.RECOMMEND, Permission.APPROVE, Permission.ADMIN},
}


class _NotSignedIn(AppError):
    status_code = 401
    code = "auth_failed"


class FakeGoogle:
    """Accounts: 1111111111 = manager with child 2222222222; 3333333333 = direct client account."""

    def __init__(self):
        self.calls: list[str] = []
        self.refresh_error: str | None = None
        self.return_refresh = True
        self.scope = "https://www.googleapis.com/auth/adwords openid email"

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.calls.append(f"{request.method} {url}")
        assert ":mutate" not in url and "/mutate" not in url, "P04 must never call mutate"
        if url.startswith("https://oauth2.googleapis.com/token"):
            form = parse_qs(request.content.decode())
            if form["grant_type"] == ["authorization_code"]:
                if form["code"] != ["good-code"]:
                    return httpx.Response(400, json={"error": "invalid_grant", "error_description": "Bad code"})
                body = {"access_token": "at-1", "scope": self.scope}
                if self.return_refresh:
                    body["refresh_token"] = REFRESH
                return httpx.Response(200, json=body)
            if self.refresh_error:
                return httpx.Response(401, json={"error": self.refresh_error, "error_description": "The OAuth client was deleted."})
            assert form["refresh_token"] == [REFRESH]
            return httpx.Response(200, json={"access_token": "at-2"})
        if url.startswith("https://oauth2.googleapis.com/revoke"):
            return httpx.Response(200)
        if url.startswith("https://openidconnect.googleapis.com/v1/userinfo"):
            return httpx.Response(200, json={"email": "ads@example.com"})
        if url.endswith("customers:listAccessibleCustomers"):
            assert request.headers["developer-token"] == "dev-token"
            return httpx.Response(200, json={"resourceNames": ["customers/1111111111", "customers/3333333333"]})
        if url.endswith("googleAds:search"):
            cid = urlparse(url).path.split("/")[3]
            q = json.loads(request.content)["query"]
            if "FROM customer_client" in q:
                assert request.headers.get("login-customer-id") == "1111111111"
                return httpx.Response(200, json={"results": [{"customerClient": {
                    "id": "2222222222", "descriptiveName": "Corporate Cars Melbourne", "currencyCode": "AUD",
                    "timeZone": "Australia/Melbourne", "manager": False, "status": "ENABLED"}}]})
            names = {"1111111111": ("Opal MCC", True), "2222222222": ("Corporate Cars Melbourne", False),
                     "3333333333": ("Direct Account", False)}
            if cid not in names:
                return httpx.Response(403, json={"error": {"code": 403, "message": "User doesn't have permission",
                                                           "status": "PERMISSION_DENIED"}})
            name, mgr = names[cid]
            return httpx.Response(200, json={"results": [{"customer": {
                "id": cid, "descriptiveName": name, "currencyCode": "AUD", "timeZone": "Australia/Sydney",
                "manager": mgr, "testAccount": False, "status": "ENABLED"}}]})
        return httpx.Response(404, json={"error": {"message": f"unexpected {url}"}})


@pytest.fixture(scope="session", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[Connection.__table__, AdsAccount.__table__])


@pytest.fixture(autouse=True)
def _clean(settings_override):
    settings_override(google_oauth_client_id="cid.apps.googleusercontent.com",
                      google_oauth_client_secret=SecretStr("csecret"), google_ads_developer_token=SecretStr("dev-token"))
    yield
    with session_scope() as db:
        for m in (AdsAccount, Connection):
            db.execute(delete(m))


@pytest.fixture
def google():
    return FakeGoogle()


@pytest.fixture
def app(google):
    from app.main import create_app
    from app.modules.p04_ads_connection.router import get_http

    application = create_app()

    def _http():
        with httpx.Client(transport=httpx.MockTransport(google.handler)) as c:
            yield c

    def _anonymous():
        raise _NotSignedIn("Not signed in", module_id="P02")

    application.dependency_overrides[get_http] = _http
    application.dependency_overrides[get_current_user] = _anonymous
    return application


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False, follow_redirects=False)


@pytest.fixture
def as_role(app):
    def _login(role="admin"):
        user = CurrentUser(id=hash(role) % 1000, email=f"{role}@example.com", name=role, role=role,
                           permissions=frozenset(_ROLE_PERMS[role]))
        app.dependency_overrides[get_current_user] = lambda: user

    return _login


@pytest.fixture
def connected(client, as_role):
    """Admin signed in and one Google connection created through the real OAuth routes."""
    as_role("admin")
    start = client.get("/api/v1/ads-connection/oauth/start")
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    cb = client.get(f"/api/v1/ads-connection/oauth/callback?code=good-code&state={state}")
    assert "connected=" in cb.headers["location"], cb.headers["location"]
    return int(parse_qs(urlparse(cb.headers["location"]).query)["connected"][0])
