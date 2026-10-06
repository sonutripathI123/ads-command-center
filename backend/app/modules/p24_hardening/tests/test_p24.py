"""P24 tests: rate limiter, security headers, retry helper, and the smoke script against our own app."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.p24_hardening import smoke
from app.modules.p24_hardening.rate_limit import InMemoryCounter, RateLimitMiddleware, build_counter
from app.modules.p24_hardening.retry import with_retry
from app.modules.p24_hardening.security_headers import SecurityHeadersMiddleware

pytestmark = pytest.mark.module("P24")


# ---- rate limiting --------------------------------------------------------------------------------------

def test_in_memory_counter_windows():
    c = InMemoryCounter()
    assert [c.incr("k", 60) for _ in range(3)] == [1, 2, 3]
    assert c.incr("other", 60) == 1  # separate key, separate count


def test_build_counter_falls_back_without_redis():
    assert isinstance(build_counter(None), InMemoryCounter)
    assert isinstance(build_counter("redis://nonexistent-host-xyz:6379/0"), InMemoryCounter)


def _rl_app(limit=2, exempt=frozenset()):
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, counter=InMemoryCounter(), limit=limit, window_seconds=60, exempt_paths=exempt)

    @app.get("/thing")
    def thing():
        return {"ok": True}

    return app


def test_rate_limit_blocks_after_limit():
    client = TestClient(_rl_app(limit=2))
    assert client.get("/thing").status_code == 200
    assert client.get("/thing").status_code == 200
    r = client.get("/thing")
    assert r.status_code == 429 and r.headers["Retry-After"] == "60"
    assert r.json()["error"]["code"] == "rate_limited"


def test_rate_limit_exempt_path_never_blocked():
    app = _rl_app(limit=1, exempt=frozenset({"/thing"}))
    client = TestClient(app)
    for _ in range(5):
        assert client.get("/thing").status_code == 200


# ---- security headers ------------------------------------------------------------------------------------

def _headers_app(hsts):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, hsts=hsts)

    @app.get("/x")
    def x():
        return {}

    return app


def test_security_headers_present():
    r = TestClient(_headers_app(hsts=False)).get("/x")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" not in r.headers


def test_hsts_only_when_enabled():
    r = TestClient(_headers_app(hsts=True)).get("/x")
    assert "max-age" in r.headers["Strict-Transport-Security"]


# ---- retry ------------------------------------------------------------------------------------------------

class Flaky(Exception):
    pass


def test_with_retry_succeeds_after_transient_errors():
    calls = {"n": 0}
    slept = []

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise Flaky("boom")
        return "ok"

    result = with_retry(flaky, retry_on=(Flaky,), attempts=5, base_delay=0.01, sleep=slept.append)
    assert result == "ok" and calls["n"] == 3 and len(slept) == 2


def test_with_retry_reraises_after_exhausting_attempts():
    def always_fails():
        raise Flaky("nope")

    with pytest.raises(Flaky):
        with_retry(always_fails, retry_on=(Flaky,), attempts=2, base_delay=0.01, sleep=lambda s: None)


def test_with_retry_does_not_catch_other_exceptions():
    def bad_input():
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        with_retry(bad_input, retry_on=(Flaky,), attempts=3, base_delay=0.01, sleep=lambda s: None)


# ---- install() wiring + smoke script against our own app --------------------------------------------------

def test_install_adds_security_headers_and_skips_rate_limit_in_test_env():
    from app.main import create_app

    client = TestClient(create_app(), raise_server_exceptions=False)
    r = client.get("/api/v1/foundation/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    for _ in range(50):  # would 429 well before this if rate limiting were active in test env
        assert client.get("/api/v1/foundation/health").status_code == 200


def test_smoke_script_against_our_own_app():
    from app.main import create_app

    # TestClient (not raw httpx+ASGITransport, which is async-only) — smoke._check only needs .request(method, path).
    client = TestClient(create_app())
    results = []
    results.append(smoke._check(client, "GET", "/api/v1/foundation/health", {200}))
    results.append(smoke._check(client, "GET", "/api/v1/auth/me", {200, 401, 422}))
    results.append(smoke._check(client, "GET", "/api/v1/does-not-exist", {200, 401, 422}))
    assert results[0][0] and results[1][0]
    assert results[2][0] is False  # 404 correctly reported as a failure


# ---- request_with_retry (Google reads) --------------------------------------------------------------------

def _fake_sleep(monkeypatch):
    import time as _t

    waits = []
    monkeypatch.setattr(_t, "sleep", waits.append)
    return waits


def _flaky(*steps):
    import httpx as _h

    it = iter(steps)
    calls = []

    def do():
        calls.append(1)
        step = next(it)
        if isinstance(step, Exception):
            raise step
        return _h.Response(step, headers={"retry-after": "2"} if step == 429 else {})

    return do, calls


def test_http_retry_recovers_from_503_and_429(monkeypatch):
    from app.modules.p24_hardening.retry import request_with_retry

    waits = _fake_sleep(monkeypatch)
    do, calls = _flaky(503, 429, 200)
    assert request_with_retry(do).status_code == 200 and len(calls) == 3 and waits == [1.0, 2.0]   # 429 honours Retry-After


def test_http_retry_returns_last_error_response_unchanged(monkeypatch):
    from app.modules.p24_hardening.retry import request_with_retry

    _fake_sleep(monkeypatch)
    do, calls = _flaky(503, 503, 503)
    assert request_with_retry(do).status_code == 503 and len(calls) == 3        # caller's own error handling still runs


def test_http_retry_does_not_retry_client_errors(monkeypatch):
    from app.modules.p24_hardening.retry import request_with_retry

    _fake_sleep(monkeypatch)
    for code in (400, 401, 403, 404):
        do, calls = _flaky(code)
        assert request_with_retry(do).status_code == code and len(calls) == 1


def test_http_retry_transport_errors(monkeypatch):
    import httpx as _h

    from app.modules.p24_hardening.retry import request_with_retry

    _fake_sleep(monkeypatch)
    do, calls = _flaky(_h.ConnectTimeout("t"), 200)
    assert request_with_retry(do).status_code == 200 and len(calls) == 2
    do, calls = _flaky(_h.ReadTimeout("a"), _h.ReadTimeout("b"), _h.ReadTimeout("c"))
    with pytest.raises(_h.ReadTimeout):
        request_with_retry(do)
    assert len(calls) == 3
