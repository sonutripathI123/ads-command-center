"""P18 tests. P03/P05/P06 replaced through their public interfaces."""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p18_monitoring import checks, interface, service
from app.modules.p18_monitoring.models import Alert, MonitorCheck
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P18")
TODAY = date(2026, 9, 29)


def days(recent: dict, base: dict, today=TODAY) -> list[dict]:
    r1, r2, b1, b2 = checks.windows(today)
    out, d = [], b1
    while d <= r2:
        out.append({"date": d.isoformat(), **(recent if d >= r1 else base)})
        d += timedelta(days=1)
    return out


BASE = {"impressions": 400, "clicks": 20, "cost": 40.0, "conversions": 1.0}  # weekly: 2800 impr, 140 clicks, AUD 280, 7 conv


def codes(sig):
    return {s.code for s in sig}


def test_windows():
    r1, r2, b1, b2 = checks.windows(TODAY)
    assert (r1, r2, b1, b2) == (date(2026, 9, 22), date(2026, 9, 28), date(2026, 8, 25), date(2026, 9, 21))


def test_quiet_week_has_no_alerts():
    assert checks.evaluate(days(BASE, BASE), TODAY, new_terms=[], recent_term_cost=280, tracking=[]) == []


def test_spikes_drops_and_changes():
    spike = checks.evaluate(days(BASE | {"cost": 120.0, "clicks": 20}, BASE), TODAY, new_terms=[], recent_term_cost=0, tracking=[])
    s = {x.code: x for x in spike}
    assert s["spend_spike"].severity == "critical" and s["cpc_change"].severity == "warning" and "spend_stopped" not in s
    stop = codes(checks.evaluate(days({"impressions": 0, "clicks": 0, "cost": 0.0, "conversions": 0.0}, BASE), TODAY,
                                 new_terms=[], recent_term_cost=0, tracking=[]))
    assert {"spend_stopped", "conversion_drop", "no_recent_data"} <= stop
    ctr = codes(checks.evaluate(days(BASE | {"clicks": 10, "cost": 20.0}, BASE), TODAY, new_terms=[], recent_term_cost=0, tracking=[]))
    assert "ctr_drop" in ctr and "cpc_change" not in ctr
    cheap = {x.code: x for x in checks.evaluate(days(BASE | {"cost": 20.0}, BASE), TODAY, new_terms=[], recent_term_cost=0, tracking=[])}
    assert cheap["cpc_change"].severity == "info"


def test_search_term_shift_and_tracking():
    new = [{"search_term": "free car rental", "cost": 90.0, "clicks": 12, "conversions": 0}]
    sig = checks.evaluate(days(BASE, BASE), TODAY, new_terms=new, recent_term_cost=200.0,
                          tracking=[{"severity": "critical", "code": "no_key_events", "title": "GA4 records no conversions", "detail": "d"},
                                    {"severity": "warning", "code": "x", "title": "minor"}])
    s = {x.code: x for x in sig}
    assert s["search_term_shift"].evidence[0][0] == "free car rental" and "tracking:no_key_events" in s and "tracking:x" not in s
    assert "search_term_shift" not in codes(checks.evaluate(days(BASE, BASE), TODAY, new_terms=new, recent_term_cost=1000.0, tracking=[]))


# ---- API ----------------------------------------------------------------------------------------------

ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="CCM")
STATE = {"daily": [], "terms": [], "health": []}


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[Alert.__table__, MonitorCheck.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    t = date.today()
    STATE.update(daily=days(BASE | {"cost": 150.0}, BASE, t), terms=[], health=[{"severity": "critical", "code": "no_key_events",
                                                                               "title": "GA4 records no conversions", "detail": ""}])
    monkeypatch.setattr(service, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(service, "summary", lambda db, a, d1, d2: {"daily": STATE["daily"]})
    monkeypatch.setattr(service, "search_terms", lambda db, a, d1, d2, limit: STATE["terms"])
    monkeypatch.setattr(service, "list_websites", lambda db: [SimpleNamespace(id=1, ads_account_id=7), SimpleNamespace(id=2, ads_account_id=7)])
    monkeypatch.setattr(service, "tracking_health", lambda db, w, d1, d2: STATE["health"])
    yield
    with session_scope() as db:
        db.execute(delete(Alert))
        db.execute(delete(MonitorCheck))


def _user(perms):
    return CurrentUser(id=1, email="me@example.com", name="me", role="x", permissions=frozenset(perms))


@pytest.fixture
def app():
    from app.main import create_app

    a = create_app()
    a.dependency_overrides[get_current_user] = lambda: _user({Permission.READ, Permission.RECOMMEND})
    return a


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


B = "/api/v1/monitoring"


def test_run_dedupes_updates_and_auto_resolves(client):
    r = client.post(f"{B}/accounts/7/run").json()
    assert r["status"] == "success" and r["opened"] == 3 and r["resolved"] == 0  # spend_spike, cpc_change, tracking (deduped over 2 sites)
    alerts = client.get(f"{B}/accounts/7").json()["alerts"]
    assert alerts[0]["severity"] == "critical" and {a["code"] for a in alerts} == {"spend_spike", "cpc_change", "tracking:no_key_events"}
    r2 = client.post(f"{B}/accounts/7/run").json()
    assert r2["opened"] == 0 and client.get(f"{B}/accounts/7").json()["alerts"][0]["occurrences"] == 2
    STATE["daily"], STATE["health"] = days(BASE, BASE, date.today()), []
    r3 = client.post(f"{B}/accounts/7/run").json()
    assert r3["resolved"] == 3 and client.get(f"{B}/accounts/7").json()["alerts"] == []
    done = client.get(f"{B}/accounts/7", params={"status": "resolved"}).json()["alerts"]
    assert len(done) == 3 and all(a["resolved_by"] == "auto" for a in done)
    assert [x["trigger"] for x in client.get(f"{B}/accounts/7").json()["runs"]] == ["manual"] * 3


def test_acknowledge_resolve_and_summary(client):
    client.post(f"{B}/accounts/7/run")
    a = client.get(f"{B}/accounts/7").json()["alerts"][0]
    ack = client.post(f"{B}/alerts/{a['id']}/status", json={"status": "acknowledged"}).json()
    assert ack["status"] == "acknowledged" and ack["acknowledged_by"] == "me@example.com"
    client.post(f"{B}/accounts/7/run")  # acknowledged alerts are still updated, not duplicated
    assert len(client.get(f"{B}/accounts/7").json()["alerts"]) == 3
    assert client.post(f"{B}/alerts/{a['id']}/status", json={"status": "gone"}).status_code == 422
    assert client.post(f"{B}/alerts/{a['id']}/status", json={"status": "resolved"}).json()["resolved_by"] == "me@example.com"
    acc = client.get(f"{B}/accounts").json()
    assert acc["scheduled_enabled"] is False and acc["accounts"][0]["open"]["critical"] == 1
    with session_scope() as db:
        assert len(interface.open_alerts(db, 7)) == 2


def test_scheduled_run_respects_flag(monkeypatch):
    with session_scope() as db:
        assert service.run_scheduled(db) == []
        monkeypatch.setattr(service, "is_enabled", lambda key, db=None: True)
        runs = service.run_scheduled(db)
        assert len(runs) == 1 and runs[0].trigger == "scheduled" and runs[0].run_by == "scheduler"


def test_failed_run_is_recorded_and_permissions(client, app, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("P05 unavailable")

    monkeypatch.setattr(service, "summary", boom)
    assert client.post(f"{B}/accounts/7/run").status_code == 500
    assert client.get(f"{B}/accounts/7").json()["runs"][0]["status"] == "failed"
    assert client.post(f"{B}/accounts/99/run").status_code == 404 and client.post(f"{B}/alerts/99999/status", json={"status": "open"}).status_code == 404
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert client.post(f"{B}/accounts/7/run").status_code == 403 and client.get(f"{B}/accounts/7").status_code == 200
