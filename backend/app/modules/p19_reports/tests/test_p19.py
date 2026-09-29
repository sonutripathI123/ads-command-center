"""P19 tests. Other modules replaced through their public interfaces."""
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p19_reports import builder, interface, render, service
from app.modules.p19_reports.models import ReportRun
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P19")
TODAY = date(2026, 9, 29)


def test_periods():
    assert builder.period("daily", TODAY)[:2] == (date(2026, 9, 28), date(2026, 9, 28))
    assert builder.period("weekly", TODAY)[:2] == (date(2026, 9, 22), date(2026, 9, 28))
    assert builder.period("monthly", TODAY) == (date(2026, 8, 1), date(2026, 8, 31), "August 2026")
    assert builder.previous(date(2026, 8, 1), date(2026, 8, 31), "monthly") == (date(2026, 7, 1), date(2026, 7, 31))
    assert builder.previous(date(2026, 3, 1), date(2026, 3, 31), "monthly") == (date(2026, 2, 1), date(2026, 2, 28))
    assert builder.previous(date(2026, 9, 22), date(2026, 9, 28), "weekly") == (date(2026, 9, 15), date(2026, 9, 21))
    for bad in [("custom", None, None), ("custom", date(2026, 9, 2), date(2026, 9, 1)), ("hourly", None, None)]:
        with pytest.raises(ValueError):
            builder.period(bad[0], TODAY, bad[1], bad[2])


def test_kpis_and_headline():
    k = builder.kpis({"cost": 150.0, "clicks": 60, "conversions": 3.0, "cost_per_conversion": 50.0},
                     {"cost": 100.0, "clicks": 50, "conversions": 0.0, "cost_per_conversion": None})
    by = {x["key"]: x for x in k}
    assert by["cost"]["change"] == 0.5 and by["conversions"]["change"] is None
    assert builder.headline(k) == ["Spend AUD 150.00 (+50% vs previous period).", "60 clicks and 3 conversions.", "Cost per conversion AUD 50.00."]


TOT = {"impressions": 1000, "clicks": 50, "cost": 120.5, "conversions": 2.0, "conversions_value": 90.0, "ctr": 0.05, "avg_cpc": 2.41,
       "cost_per_conversion": 60.25}
FUNNEL = {"stages": [{"label": "Ad clicks", "value": 50, "rate": 0.05, "cost_per": 2.41, "source": "Google Ads", "estimated": False},
                     {"label": "Leads", "value": None, "rate": None, "cost_per": None, "source": "GA4", "estimated": True}],
          "bottlenecks": [{"code": "leads_not_measured", "severity": "critical", "title": "No lead event in GA4"}]}
OV = {"totals": {"sessions": 100, "engaged_sessions": 60, "users": 80, "key_events": 0.0}, "ga4_first_day": date(2026, 9, 14),
      "channels": [{"channel": "Paid Search", "sessions": 70, "engaged_sessions": 40, "key_events": 0.0}],
      "top_queries": [{"query": "chauffeur <melbourne>", "clicks": 3, "impressions": 90, "position": 12.4}],
      "organic_totals": {"clicks": 3, "impressions": 90},
      "bookings": {"count": 0, "revenue": 0.0, "google_ads": {"count": 0, "revenue": 0.0}, "by_channel": []},
      "health": [{"severity": "critical", "code": "no_key_events", "title": "GA4 records no conversions", "detail": "d"},
                 {"severity": "info", "code": "i", "title": "fyi", "detail": ""}]}


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[ReportRun.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    calls = []
    monkeypatch.setattr(service, "list_accounts", lambda db: [SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="CCM")])
    monkeypatch.setattr(service, "list_websites", lambda db: [SimpleNamespace(id=1, name="Corporate Cars", ads_account_id=7)])

    def summ(db, a, d1, d2):
        calls.append((d1, d2))
        return {"totals": TOT if len(calls) % 2 else TOT | {"cost": 100.0}}

    monkeypatch.setattr(service, "summary", summ)
    monkeypatch.setattr(service, "campaigns", lambda db, a, d1, d2: [
        {"name": "Search", "status": "ENABLED", "clicks": 50, "cost": 120.5, "conversions": 2.0, "cost_per_conversion": 60.25},
        {"name": "Idle", "status": "PAUSED", "clicks": 0, "cost": 0.0, "conversions": 0.0, "cost_per_conversion": None}])
    monkeypatch.setattr(service, "search_terms", lambda db, a, d1, d2, limit: [{"search_term": "airport chauffeur", "clicks": 9, "cost": 30.0, "conversions": 1.0}])
    monkeypatch.setattr(service, "website_funnel", lambda db, w, d1, d2: FUNNEL)
    monkeypatch.setattr(service, "open_recommendations", lambda db, a: [{"priority": 1, "severity": "critical", "title": "Fix tracking", "status": "proposed"}])
    monkeypatch.setattr(service, "decisions", lambda db, a, d1, d2: [{"title": "Add 3 negatives", "status": "approved", "decided_by": "me", "decided_at": "2026-09-25T01:00:00"}])
    monkeypatch.setattr(service, "open_alerts", lambda db, a: [{"severity": "critical", "title": "Tracking broken", "action": "Fix it"}])
    monkeypatch.setattr(service, "website_overview", lambda db, w, d1, d2: OV)
    yield calls
    with session_scope() as db:
        db.execute(delete(ReportRun))


@pytest.fixture
def client():
    from app.main import create_app

    a = create_app()
    a.dependency_overrides[get_current_user] = lambda: CurrentUser(id=1, email="viewer@x", name="v", role="viewer",
                                                                    permissions=frozenset({Permission.READ}))
    return TestClient(a, raise_server_exceptions=False)


B = "/api/v1/reports"


def test_account_report_snapshot_csv_html(client, fakes):
    r = client.post(f"{B}/runs", json={"scope": "account", "scope_id": 7, "period": "custom", "date_from": "2026-09-01", "date_to": "2026-09-07"})
    assert r.status_code == 201, r.text  # viewers can generate (read-only)
    rep = r.json()
    assert fakes == [(date(2026, 9, 1), date(2026, 9, 7)), (date(2026, 8, 25), date(2026, 8, 31))]
    c = rep["content"]
    assert rep["title"] == "Custom Google Ads report — CCM" and c["headline"][0] == "Spend AUD 120.50 (+20% vs previous period)."
    assert [x["name"] for x in c["campaigns"]] == ["Search"] and c["funnels"][0]["website"] == "Corporate Cars"
    assert c["recommendations"][0]["title"] == "Fix tracking" and c["approvals"][0]["status"] == "approved" and c["alerts"]
    csv = client.get(f"{B}/runs/{rep['id']}/csv")
    assert "attachment" in csv.headers["content-disposition"]
    for section in ("Key figures", "Campaigns", "Top search terms by cost", "Funnel — Corporate Cars", "Open recommendations",
                    "Approval decisions", "Open alerts"):
        assert section in csv.text
    assert "not measured" in csv.text and "+20%" in csv.text
    page = client.get(f"{B}/runs/{rep['id']}/html").text
    assert page.startswith("<!doctype html>") and "window.print()" in page and "@media print" in page
    assert [x["id"] for x in client.get(f"{B}/runs").json()] == [rep["id"]] and "content" not in client.get(f"{B}/runs").json()[0]


def test_website_report_escapes_and_notes(client):
    rep = client.post(f"{B}/runs", json={"scope": "website", "scope_id": 1, "period": "weekly"}).json()
    c = rep["content"]
    assert c["headline"][2] == "0 bookings, AUD 0.00 revenue." and [i["code"] for i in c["issues"]] == ["no_key_events"]
    page = client.get(f"{B}/runs/{rep['id']}/html").text
    assert "chauffeur &lt;melbourne&gt;" in page and "<melbourne>" not in page
    assert "GA4 data starts on 2026-09-14" in page or rep["date_from"] >= "2026-09-14"


def test_validation_and_interface(client):
    assert client.post(f"{B}/runs", json={"scope": "planet", "scope_id": 1}).status_code == 422
    assert client.post(f"{B}/runs", json={"scope": "account", "scope_id": 99}).status_code == 404
    assert client.post(f"{B}/runs", json={"scope": "website", "scope_id": 1, "period": "custom"}).status_code == 422
    assert client.get(f"{B}/runs/999999").status_code == 404
    opts = client.get(f"{B}/options").json()
    assert opts["periods"] == ["daily", "weekly", "monthly", "custom"] and opts["accounts"][0]["name"] == "CCM"
    with session_scope() as db:
        r = interface.generate_report(db, scope="account", scope_id=7, period="daily", by="scheduler")
    assert r["period"] == "daily" and r["created_by"] == "scheduler"


def test_render_number_alignment():
    assert render._num("1,234.50") and render._num("+20%") and render._num("-3") and not render._num("Search")
