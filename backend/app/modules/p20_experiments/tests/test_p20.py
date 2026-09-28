"""P20 tests. P05/P06/P03/P16 replaced through their public interfaces."""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p20_experiments import interface, service, stats
from app.modules.p20_experiments.models import Experiment
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P20")


def m(imp, clicks, cost, conv):
    return {"impressions": imp, "clicks": clicks, "cost": cost, "conversions": conv,
            "ctr": clicks / imp if imp else None, "avg_cpc": round(cost / clicks, 2) if clicks else None,
            "conv_rate": conv / clicks if clicks else None, "cost_per_conversion": round(cost / conv, 2) if conv else None}


# ---- stats --------------------------------------------------------------------------------------------

def test_two_proportion():
    assert stats.two_proportion(50, 1000, 50, 1000) == pytest.approx(1.0)
    assert stats.two_proportion(50, 1000, 90, 1000) < 0.01
    assert stats.two_proportion(0, 0, 1, 10) is None and stats.two_proportion(0, 10, 0, 10) is None


def test_compare_verdicts():
    a, b = m(10000, 500, 1000, 20), m(10000, 700, 1050, 35)
    r = stats.compare(a, b, primary="ctr", min_clicks=100)
    row = {x["metric"]: x for x in r["rows"]}
    assert r["verdict"] == "variant_better" and row["ctr"]["p_value"] < 0.05 and row["ctr"]["lift"] == 0.4
    assert row["avg_cpc"]["direction"] == "better" and row["avg_cpc"]["test"] == "directional"
    assert stats.compare(b, a, primary="ctr", min_clicks=100)["verdict"] == "control_better"
    assert stats.compare(a, m(10000, 510, 1000, 20), primary="ctr", min_clicks=100)["verdict"] == "no_significant_difference"
    assert stats.compare(a, b, primary="ctr", min_clicks=600)["verdict"] == "insufficient_data"
    assert stats.compare(a, b, primary="cost_per_conversion", min_clicks=100)["verdict"] == "directional_variant_better"


# ---- API ----------------------------------------------------------------------------------------------

ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="CCM")
SITE = SimpleNamespace(id=1, ads_account_id=7)
TODAY = date.today()
APPROVALS: dict[int, dict] = {}
BASE_START = TODAY - timedelta(days=60)


def _campaigns(db, a, d1, d2):
    # baseline window (before BASE_START+30) → weaker CTR; later windows → stronger
    late = d1 >= BASE_START + timedelta(days=30)
    return [{"google_id": "c1", "name": "Search A", "status": "ENABLED", **(m(20000, 1400, 2800, 40) if late else m(20000, 1000, 2500, 30))},
            {"google_id": "c2", "name": "Search B", "status": "PAUSED", **m(20000, 1000, 2000, 30)}]


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[Experiment.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    APPROVALS.clear()
    monkeypatch.setattr(service, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(service, "campaigns", _campaigns)
    monkeypatch.setattr(service, "ad_groups", lambda db, a, d1, d2: [])
    monkeypatch.setattr(service, "ads", lambda db, a, d1, d2: [])
    monkeypatch.setattr(service, "list_websites", lambda db: [SITE])
    monkeypatch.setattr(service, "tracking_health", lambda db, w, d1, d2: [{"severity": "critical", "title": "GA4 records no key events"}])

    def request_approval(db, **kw):
        i = len(APPROVALS) + 1
        APPROVALS[i] = {"id": i, "status": "pending", **kw}
        return APPROVALS[i]

    monkeypatch.setattr(service, "request_approval", request_approval)
    monkeypatch.setattr(service, "get_approval", lambda db, i: APPROVALS.get(i))
    yield
    with session_scope() as db:
        db.execute(delete(Experiment))


def _user(perms):
    return CurrentUser(id=1, email="me@example.com", name="me", role="x", permissions=frozenset(perms))


@pytest.fixture
def app():
    from app.main import create_app

    a = create_app()
    a.dependency_overrides[get_current_user] = lambda: _user({Permission.READ, Permission.RECOMMEND, Permission.APPROVE})
    return a


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


B = "/api/v1/experiments"


def _ab(**kw):
    return {"name": "A vs B", "hypothesis": "B's copy lifts CTR", "kind": "a_b", "entity_type": "campaign", "control_ref": "c2",
            "variant_ref": "c1", "primary_metric": "ctr", "start_date": str(TODAY - timedelta(days=20)),
            "end_date": str(TODAY + timedelta(days=10))} | kw


def _ba(**kw):
    return {"name": "New ads", "kind": "before_after", "entity_type": "campaign", "control_ref": "c1", "primary_metric": "ctr",
            "baseline_start": str(BASE_START), "baseline_end": str(BASE_START + timedelta(days=29)),
            "start_date": str(BASE_START + timedelta(days=30)), "end_date": str(TODAY - timedelta(days=1))} | kw


def test_meta_and_entities(client):
    assert {x["key"] for x in client.get(f"{B}/meta").json()["metrics"]} == {"ctr", "conv_rate", "avg_cpc", "cost_per_conversion"}
    ents = client.get(f"{B}/accounts/7/entities", params={"entity_type": "campaign"}).json()
    assert [e["ref"] for e in ents] == ["c1", "c2"] and ents[0]["label"] == "Search A"
    assert client.get(f"{B}/accounts/7/entities", params={"entity_type": "nope"}).status_code == 422
    assert client.get(f"{B}/accounts/99/entities", params={"entity_type": "campaign"}).status_code == 404


def test_validation(client):
    for bad in [_ab(variant_ref="c2"), _ab(variant_ref="zz"), _ab(control_ref="zz"), _ab(kind="x"), _ab(primary_metric="roas"),
                _ab(end_date=str(TODAY - timedelta(days=30))), _ab(min_clicks=1), _ba(baseline_start=None),
                _ba(baseline_end=str(TODAY))]:
        assert client.post(f"{B}/accounts/7", json=bad).status_code == 422, bad


def test_ab_lifecycle(client):
    r = client.post(f"{B}/accounts/7", json=_ab())
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["status"] == "draft" and e["control_label"] == "Search B" and e["variant_label"] == "Search A"
    eid = e["id"]
    assert client.patch(f"{B}/{eid}", json={"min_clicks": 200}).json()["min_clicks"] == 200
    assert client.patch(f"{B}/{eid}", json={"status": "running"}).status_code == 422  # not editable
    assert client.post(f"{B}/{eid}/start").status_code == 422  # not submitted
    r = client.post(f"{B}/{eid}/submit").json()
    assert r["status"] == "pending_approval" and r["approval_status"] == "pending"
    a = APPROVALS[r["approval_id"]]
    assert a["change_type"] == "start_experiment" and a["source_ref"] == f"P20|experiment|{eid}"
    assert a["after"]["variant"] == "Search A"
    assert client.patch(f"{B}/{eid}", json={"name": "x"}).status_code == 422  # locked after submit
    assert client.post(f"{B}/{eid}/start").status_code == 422  # still pending
    a["status"] = "approved"
    assert client.post(f"{B}/{eid}/start").json()["status"] == "running"
    res = client.post(f"{B}/{eid}/analyze").json()
    assert res["verdict"] == "variant_better" and res["control"]["clicks"] == 1000 and res["variant"]["clicks"] == 1400
    assert any("not finished" in x for x in res["limitations"]) and any("tracking" in x for x in res["limitations"])
    assert client.get(f"{B}/{eid}").json()["results"]["verdict"] == "variant_better"  # stored while running
    assert client.post(f"{B}/{eid}/complete", json={"conclusion": " "}).status_code == 422
    done = client.post(f"{B}/{eid}/complete", json={"conclusion": "Roll B's copy out"}).json()
    assert done["status"] == "completed" and done["conclusion"] == "Roll B's copy out"
    assert client.post(f"{B}/{eid}/cancel").status_code == 422
    with session_scope() as db:
        assert interface.experiments_summary(db, 7)[0]["status"] == "completed"


def test_before_after_and_rejection(client):
    e = client.post(f"{B}/accounts/7", json=_ba()).json()
    res = client.post(f"{B}/{e['id']}/analyze").json()  # preview allowed in draft, not stored
    assert res["control"]["clicks"] == 1000 and res["variant"]["clicks"] == 1400 and res["verdict"] == "variant_better"
    assert any("seasonality" in x for x in res["limitations"])
    assert client.get(f"{B}/{e['id']}").json()["results"] is None
    sub = client.post(f"{B}/{e['id']}/submit").json()
    APPROVALS[sub["approval_id"]]["status"] = "rejected"
    r = client.post(f"{B}/{e['id']}/start")
    assert r.status_code == 422 and "rejected" in r.text
    assert client.get(f"{B}/{e['id']}").json()["status"] == "draft"
    assert client.post(f"{B}/{e['id']}/cancel").json()["status"] == "cancelled"
    future = client.post(f"{B}/accounts/7", json=_ab(start_date=str(TODAY + timedelta(days=5)),
                                                     end_date=str(TODAY + timedelta(days=9)))).json()
    assert client.post(f"{B}/{future['id']}/analyze").status_code == 422


def test_permissions(client, app):
    eid = client.post(f"{B}/accounts/7", json=_ab()).json()["id"]
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert client.post(f"{B}/accounts/7", json=_ab()).status_code == 403
    assert client.post(f"{B}/{eid}/submit").status_code == 403
    assert client.get(f"{B}/accounts/7").status_code == 200 and client.get(f"{B}/{eid}").status_code == 200
    assert client.get(f"{B}/999999").status_code == 404
