from datetime import UTC, datetime, timedelta

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modules.p02_auth.interface import SESSION_COOKIE, Permission, require_permission
from app.modules.p02_auth.models import Session, User
from app.modules.p02_auth.security import hash_password, token_hash, verify_password
from app.shared.db import session_scope

from .conftest import PASSWORD

pytestmark = pytest.mark.module("P02")


def test_password_hash_roundtrip():
    h = hash_password("a-long-password-123")
    assert h.startswith("scrypt$") and verify_password("a-long-password-123", h)
    assert not verify_password("wrong", h) and not verify_password("x", None) and not verify_password("x", "junk")


def test_login_sets_httponly_cookie_and_me_works(client, login, make_user):
    make_user()
    r = login()
    assert r.status_code == 200 and r.json()["role"] == "admin"
    cookie = r.headers["set-cookie"]
    assert SESSION_COOKIE in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "admin@example.com"
    assert "execute" not in me.json()["permissions"]


def test_session_token_stored_hashed(client, login, make_user):
    make_user()
    login()
    raw = client.cookies.get(SESSION_COOKIE)
    with session_scope() as db:
        hashes = [s.token_hash for s in db.scalars(select(Session))]
    assert raw not in hashes and token_hash(raw) in hashes


def test_wrong_password_and_unknown_email_look_identical(login, make_user):
    make_user()
    a, b = login(password="nope-nope-nope"), login(email="ghost@example.com")
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["message"] == b.json()["error"]["message"]


def test_throttle_after_five_failures(login, make_user):
    make_user()
    for _ in range(5):
        assert login(password="bad-password-x").status_code == 401
    assert login().status_code == 429  # even the right password is blocked for now


def test_inactive_user_cannot_login(login, make_user):
    uid = make_user()
    with session_scope() as db:
        db.get(User, uid).is_active = False
    assert login().status_code == 401


def test_expired_session_rejected(client, login, make_user):
    make_user()
    login()
    with session_scope() as db:
        for s in db.scalars(select(Session)):
            s.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_revokes_session(client, login, make_user):
    make_user()
    login()
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_requires_login(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["error"]["module_id"] == "P02"


def test_foreign_origin_rejected(client, make_user):
    make_user()
    r = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": PASSWORD},
                    headers={"origin": "https://evil.example"})
    assert r.status_code == 403


def test_allowed_origin_accepted(client, make_user):
    make_user()
    r = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": PASSWORD},
                    headers={"origin": "http://localhost:3000"})
    assert r.status_code == 200


def test_require_permission_dependency(make_user):
    from app.main import create_app

    app = create_app()
    r = APIRouter()

    @r.get("/needs-recommend")
    def _needs(user=Depends(require_permission(Permission.RECOMMEND))):
        return {"ok": user.email}

    app.include_router(r)
    c = TestClient(app)
    make_user("viewer@example.com", role="viewer")
    make_user("analyst@example.com", role="analyst")
    assert c.get("/needs-recommend").status_code == 401
    c.post("/api/v1/auth/login", json={"email": "viewer@example.com", "password": PASSWORD})
    assert c.get("/needs-recommend").status_code == 403
    c.post("/api/v1/auth/login", json={"email": "analyst@example.com", "password": PASSWORD})
    assert c.get("/needs-recommend").status_code == 200


def test_execute_only_via_per_user_switch(client, login, make_user):
    make_user(execute=True)
    login()
    assert "execute" in client.get("/api/v1/auth/me").json()["permissions"]
