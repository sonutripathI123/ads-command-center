import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.main import create_app
from app.shared.errors import NotFoundError

pytestmark = pytest.mark.module("P00")


@pytest.fixture
def client():
    return TestClient(create_app(), raise_server_exceptions=False)


def test_health_ok_and_reports_kill_switch(client):
    r = client.get("/api/v1/foundation/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] is True
    assert body["execution_kill_switch"] is True


def test_request_id_is_echoed(client):
    r = client.get("/api/v1/foundation/health", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"


def test_modules_lists_full_registry(client):
    ids = [m["id"] for m in client.get("/api/v1/foundation/modules").json()]
    assert ids == [f"P{i:02d}" for i in range(25)]


def test_flags_all_off_by_default(client):
    flags = {f["key"]: f for f in client.get("/api/v1/foundation/flags").json()}
    assert "ads.execution.enabled" in flags
    assert all(not f["enabled"] for f in flags.values())
    assert flags["ads.execution.enabled"]["source"] == "kill_switch"


def test_no_flag_write_endpoint(client):
    assert client.post("/api/v1/foundation/flags", json={}).status_code == 405
    assert client.put("/api/v1/foundation/flags", json={}).status_code == 405


def test_app_error_envelope():
    app = create_app()
    r = APIRouter()

    @r.get("/boom")
    def boom():
        raise NotFoundError("nope", module_id="P99", details={"x": 1})

    app.include_router(r)
    res = TestClient(app).get("/boom", headers={"x-request-id": "rid"})
    assert res.status_code == 404
    assert res.json() == {"error": {"code": "not_found", "message": "nope", "module_id": "P99",
                                    "request_id": "rid", "details": {"x": 1}}}


def test_unhandled_error_does_not_leak_details():
    app = create_app()
    r = APIRouter()

    @r.get("/crash")
    def crash():
        raise RuntimeError("secret internals")

    app.include_router(r)
    res = TestClient(app, raise_server_exceptions=False).get("/crash")
    assert res.status_code == 500
    assert "secret internals" not in res.text
