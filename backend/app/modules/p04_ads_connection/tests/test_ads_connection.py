from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

from app.modules.p04_ads_connection.crypto import decrypt
from app.modules.p04_ads_connection.models import Connection
from app.shared.db import session_scope

from .conftest import REFRESH

pytestmark = pytest.mark.module("P04")
B = "/api/v1/ads-connection"


def test_status_requires_login(client):
    assert client.get(f"{B}/status").status_code == 401


def test_status_reports_configuration(client, as_role):
    as_role("viewer")
    s = client.get(f"{B}/status").json()
    assert s["oauth_client_configured"] and s["developer_token_configured"] and s["api_version"] == "v25"
    assert s["redirect_uri"].endswith("/api/v1/ads-connection/oauth/callback")


def test_only_admin_can_start_oauth(client, as_role):
    as_role("analyst")
    assert client.get(f"{B}/oauth/start").status_code == 403


def test_oauth_start_redirects_to_google_with_offline_adwords(client, as_role):
    as_role("admin")
    r = client.get(f"{B}/oauth/start")
    assert r.status_code == 303
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert "https://www.googleapis.com/auth/adwords" in q["scope"][0]
    assert q["access_type"] == ["offline"] and q["prompt"] == ["consent"]
    assert "p04_oauth_nonce" in r.headers["set-cookie"] and "HttpOnly" in r.headers["set-cookie"]


def test_callback_stores_encrypted_refresh_token(client, connected):
    with session_scope() as db:
        conn = db.get(Connection, connected)
        assert conn.google_email == "ads@example.com" and conn.status == "active"
        assert REFRESH not in conn.refresh_token_enc and decrypt(conn.refresh_token_enc) == REFRESH
    assert REFRESH not in client.get(f"{B}/status").text


def test_callback_rejects_forged_state(client, as_role):
    as_role("admin")
    client.get(f"{B}/oauth/start")
    r = client.get(f"{B}/oauth/callback?code=good-code&state=1.abc.9999999999.deadbeef")
    assert "error=" in r.headers["location"]
    with session_scope() as db:
        assert db.scalar(select(Connection)) is None


def test_callback_without_nonce_cookie_rejected(client, as_role):
    as_role("admin")
    start = client.get(f"{B}/oauth/start")
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    client.cookies.delete("p04_oauth_nonce")
    r = client.get(f"{B}/oauth/callback?code=good-code&state={state}")
    assert "error=" in r.headers["location"]


def test_callback_user_denied(client, as_role):
    as_role("admin")
    r = client.get(f"{B}/oauth/callback?error=access_denied")
    assert "error=Google" in r.headers["location"]


def test_callback_without_refresh_token_explains(client, as_role, google):
    google.return_refresh = False
    as_role("admin")
    start = client.get(f"{B}/oauth/start")
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    r = client.get(f"{B}/oauth/callback?code=good-code&state={state}")
    assert "refresh+token" in r.headers["location"]


def test_discover_includes_manager_children(client, connected):
    found = {a["customer_id"]: a for a in client.get(f"{B}/connections/{connected}/discover").json()}
    assert set(found) == {"1111111111", "2222222222", "3333333333"}
    assert found["1111111111"]["is_manager"] is True
    assert found["2222222222"]["login_customer_id"] == "1111111111"
    assert found["3333333333"]["login_customer_id"] is None


def test_add_account_via_manager_and_listed(client, connected):
    r = client.post(f"{B}/accounts", json={"connection_id": connected, "customer_id": "222-222-2222",
                                           "login_customer_id": "111-111-1111"})
    assert r.status_code == 201, r.text
    acc = r.json()
    assert acc["customer_id"] == "2222222222" and acc["descriptive_name"] == "Corporate Cars Melbourne"
    assert acc["login_customer_id"] == "1111111111"
    assert [a["customer_id"] for a in client.get(f"{B}/status").json()["accounts"]] == ["2222222222"]
    disc = {a["customer_id"]: a for a in client.get(f"{B}/connections/{connected}/discover").json()}
    assert disc["2222222222"]["already_added"] is True


def test_add_account_bad_id(client, connected):
    assert client.post(f"{B}/accounts", json={"connection_id": connected, "customer_id": "123"}).status_code == 422


def test_add_inaccessible_account_surfaces_google_error(client, connected):
    r = client.post(f"{B}/accounts", json={"connection_id": connected, "customer_id": "9999999999"})
    assert r.status_code == 502 and r.json()["error"]["details"]["reason"] == "PERMISSION_DENIED"


def test_check_connection_ok_and_deleted_client(client, connected, google):
    r = client.post(f"{B}/connections/{connected}/check")
    assert r.status_code == 200 and r.json()["accessible_customer_ids"] == ["1111111111", "3333333333"]
    google.refresh_error = "deleted_client"
    r = client.post(f"{B}/connections/{connected}/check")
    assert r.status_code == 502 and "deleted" in r.json()["error"]["message"]
    conn = client.get(f"{B}/status").json()["connections"][0]
    assert conn["status"] == "error" and "deleted" in conn["last_error"]


def test_disconnect_revokes_and_disables_accounts(client, connected, google):
    client.post(f"{B}/accounts", json={"connection_id": connected, "customer_id": "3333333333"})
    r = client.post(f"{B}/connections/{connected}/disconnect")
    assert r.status_code == 200 and r.json()["status"] == "revoked"
    assert any("revoke" in c for c in google.calls)
    s = client.get(f"{B}/status").json()
    assert s["accounts"][0]["status"] == "disabled"
    with session_scope() as db:
        assert db.get(Connection, connected).refresh_token_enc is None


def test_non_admin_cannot_add_or_discover(client, connected, as_role):
    client.post("/api/v1/auth/logout")
    as_role("approver")
    assert client.get(f"{B}/connections/{connected}/discover").status_code == 403
    assert client.post(f"{B}/accounts", json={"connection_id": connected, "customer_id": "3333333333"}).status_code == 403


def test_missing_oauth_client_is_clear_error(client, as_role, settings_override):
    settings_override(google_oauth_client_id=None)
    as_role("admin")
    r = client.get(f"{B}/oauth/start")
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_configured"


def test_interface_read_session(client, connected, google):
    import httpx

    from app.modules.p04_ads_connection.interface import active_accounts, open_read_session

    client.post(f"{B}/accounts", json={"connection_id": connected, "customer_id": "3333333333"})
    with session_scope() as db, httpx.Client(transport=httpx.MockTransport(google.handler)) as http:
        accs = active_accounts(db)
        assert [a.customer_id for a in accs] == ["3333333333"]
        rows = open_read_session(db, accs[0].id, http).search("SELECT customer.id FROM customer")
        assert rows[0]["customer"]["id"] == "3333333333"


def test_search_rejects_non_select():
    import httpx

    from app.modules.p04_ads_connection.adapters.google_ads import GoogleAdsReadClient

    c = GoogleAdsReadClient(httpx.Client(), client_id="x", client_secret="y", developer_token="d", api_version="v26")
    with pytest.raises(ValueError):
        c.search("at", "123", "UPDATE campaign SET x")
