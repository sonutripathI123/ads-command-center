import pytest

from .conftest import PASSWORD

pytestmark = pytest.mark.module("P02")
U = "/api/v1/auth/users"


def test_non_admin_cannot_manage_users(client, login, make_user):
    make_user("analyst@example.com", role="analyst")
    login("analyst@example.com")
    assert client.get(U).status_code == 403
    assert client.post(U, json={"email": "x@example.com", "role": "viewer", "password": PASSWORD}).status_code == 403


def test_admin_creates_and_lists_users(client, login, make_user):
    make_user()
    login()
    r = client.post(U, json={"email": "New@Example.com ", "name": "New", "role": "viewer", "password": PASSWORD})
    assert r.status_code == 201
    assert r.json()["email"] == "new@example.com" and r.json()["execute_enabled"] is False
    assert "password_hash" not in r.text
    assert {u["email"] for u in client.get(U).json()} == {"admin@example.com", "new@example.com"}


@pytest.mark.parametrize("body,code", [
    ({"email": "a@example.com", "role": "superuser", "password": PASSWORD}, 422),
    ({"email": "a@example.com", "role": "viewer", "password": "short"}, 422),
    ({"email": "admin@example.com", "role": "viewer", "password": PASSWORD}, 422),
])
def test_create_user_validation(client, login, make_user, body, code):
    make_user()
    login()
    assert client.post(U, json=body).status_code == code


def test_execute_cannot_be_granted_via_api(client, login, make_user):
    make_user()
    uid = make_user("v@example.com", role="viewer")
    login()
    r = client.patch(f"{U}/{uid}", json={"execute_enabled": True, "role": "approver"})
    assert r.status_code == 200
    assert r.json()["role"] == "approver" and r.json()["execute_enabled"] is False
    r = client.post(U, json={"email": "e@example.com", "role": "viewer", "password": PASSWORD, "execute_enabled": True})
    assert r.json()["execute_enabled"] is False


def test_last_admin_protected(client, login, make_user):
    uid = make_user()
    login()
    assert client.patch(f"{U}/{uid}", json={"role": "viewer"}).status_code == 403
    assert client.patch(f"{U}/{uid}", json={"is_active": False}).status_code == 403


def test_deactivating_user_kills_their_sessions(client, login, make_user):
    from fastapi.testclient import TestClient

    from app.main import create_app

    make_user()
    vid = make_user("v@example.com", role="viewer")
    other = TestClient(create_app())
    other.post("/api/v1/auth/login", json={"email": "v@example.com", "password": PASSWORD})
    assert other.get("/api/v1/auth/me").status_code == 200
    login()
    assert client.patch(f"{U}/{vid}", json={"is_active": False}).status_code == 200
    assert other.get("/api/v1/auth/me").status_code == 401
