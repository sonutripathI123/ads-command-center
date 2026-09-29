"""P13 tests. P03/P05/P06 replaced through their public interfaces."""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p13_booking_funnel import funnel, interface, service

pytestmark = pytest.mark.module("P13")

ADS = {"impressions": 10000, "clicks": 500, "cost": 1500.0, "conversions": 20.0, "conversions_value": 900.0, "cost_per_conversion": 75.0}


def ov(first_day=None, lead=True, sessions=(400, 100)):
    events = [{"event_name": "form_start", "event_count": 80, "role": None, "suggested_role": "micro"}]
    if lead:
        events.append({"event_name": "generate_lead", "event_count": 40, "role": "lead", "suggested_role": "lead"})
    return {"totals": {"sessions": sessions[0] + sessions[1]}, "ga4_first_day": first_day,
            "channels": [{"channel": "Paid Search", "sessions": sessions[0]}, {"channel": "Direct", "sessions": sessions[1]}],
            "events": events, "bookings": {"count": 5, "revenue": 2000.0, "google_ads": {"count": 4, "revenue": 1200.0},
                                           "by_channel": [{"channel": "Google Ads", "count": 4, "revenue": 1200.0},
                                                          {"channel": "phone", "count": 1, "revenue": 800.0}]}}


def test_stages_rates_costs_and_estimate():
    ga = funnel.ga4_counts(ov())
    st = {s.key: s for s in funnel.build(ADS, ga, ov()["bookings"], prev={"clicks": 400, "bookings": 2})}
    assert st["clicks"].rate == 0.05 and st["clicks"].cost_per == 3.0 and st["clicks"].change == 0.25
    assert st["visits"].value == 400 and st["visits"].rate == 0.8
    assert st["leads"].value == 32.0 and st["leads"].estimated  # 40 leads × 80% paid share
    assert st["bookings"].value == 4 and st["bookings"].rate == 0.125 and st["bookings"].cost_per == 375.0 and st["bookings"].change == 1.0
    assert st["revenue"].value == 1200.0 and st["revenue"].rate is None


def test_not_measured_is_none_not_zero():
    ga = funnel.ga4_counts(ov(lead=False))
    st = {s.key: s for s in funnel.build(None, ga, None)}
    assert st["clicks"].value is None and st["leads"].value is None and st["bookings"].value is None
    codes = {b.code for b in funnel.bottlenecks(list(st.values()), None, ga, None)}
    assert {"no_ads_account", "leads_not_measured", "bookings_not_measured"} <= codes and "low_lead_rate" not in codes
    assert {b.code for b in funnel.bottlenecks(funnel.build(None, {"measured": False}, None), None, {"measured": False}, None)} >= {"no_ga4"}


def test_bottlenecks_on_weak_funnel():
    weak = ADS | {"impressions": 50000, "clicks": 1000, "cost": 3000.0}
    o = ov(sessions=(300, 100))
    o["events"][1]["event_count"] = 5
    bk = o["bookings"] | {"google_ads": {"count": 0, "revenue": 0.0}}
    ga = funnel.ga4_counts(o)
    codes = {b.code for b in funnel.bottlenecks(funnel.build(weak, ga, bk), weak, ga, bk)}
    assert {"low_ctr", "clicks_lost", "no_ads_bookings"} <= codes
    bk2 = o["bookings"] | {"google_ads": {"count": 1, "revenue": 500.0}}
    o["events"][1]["event_count"] = 200
    ga2 = funnel.ga4_counts(o)
    codes2 = {b.code for b in funnel.bottlenecks(funnel.build(weak, ga2, bk2), weak, ga2, bk2)}
    assert {"roas_below_1", "low_booking_rate"} <= codes2


def test_partial_ga4_skips_click_to_visit():
    ga = funnel.ga4_counts(ov())
    st = {s.key: s for s in funnel.build(ADS, ga, None, ga4_partial=True)}
    assert st["visits"].rate is None and st["leads"].rate == 0.08
    codes = [b.code for b in funnel.bottlenecks(list(st.values()), ADS, ga, None, ga4_from="2026-09-14")]
    assert codes[0] == "ga4_partial" and "clicks_lost" not in codes


# ---- API ----------------------------------------------------------------------------------------------

SITE = SimpleNamespace(id=1, name="CCM", domain="x.com.au", ads_account_id=7)
CALLS: list = []


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    CALLS.clear()
    monkeypatch.setattr(service, "list_websites", lambda db: [SITE, SimpleNamespace(id=2, name="Other", domain="o.com.au", ads_account_id=None)])
    monkeypatch.setattr(service, "list_accounts", lambda db: [SimpleNamespace(id=7)])

    def summ(db, a, d1, d2):
        CALLS.append((d1, d2))
        return {"totals": ADS}

    monkeypatch.setattr(service, "summary", summ)
    monkeypatch.setattr(service, "website_overview", lambda db, w, d1, d2: ov(first_day=date(2026, 1, 1)))
    monkeypatch.setattr(service, "bookings_summary", lambda db, d1, d2, w: {"count": 5 if w == 1 else 0})
    monkeypatch.setattr(service, "campaigns", lambda db, a, d1, d2: [
        {"google_id": "1", "name": "Search", "status": "PAUSED", "impressions": 100, "clicks": 10, "cost": 50.0, "conversions": 2.0,
         "conversions_value": 100.0, "cost_per_conversion": 25.0, "conv_rate": 0.2},
        {"google_id": "2", "name": "Idle", "status": "PAUSED", "impressions": 0, "clicks": 0, "cost": 0.0, "conversions": 0.0,
         "conversions_value": 0.0, "cost_per_conversion": None, "conv_rate": None}])


@pytest.fixture
def client():
    from app.main import create_app

    a = create_app()
    a.dependency_overrides[get_current_user] = lambda: CurrentUser(id=1, email="me@x", name="me", role="viewer",
                                                                    permissions=frozenset({Permission.READ}))
    return TestClient(a, raise_server_exceptions=False)


def test_api_funnel_and_previous_period(client):
    assert [w["id"] for w in client.get("/api/v1/funnel/websites").json()] == [1, 2]
    r = client.get("/api/v1/funnel/websites/1", params={"date_from": "2026-09-01", "date_to": "2026-09-10"})
    assert r.status_code == 200, r.text
    f = r.json()
    assert f["period"]["previous_from"] == "2026-08-22" and f["period"]["previous_to"] == "2026-08-31"
    assert CALLS == [(date(2026, 9, 1), date(2026, 9, 10)), (date(2026, 8, 22), date(2026, 8, 31))]
    assert [c["name"] for c in f["campaigns"]] == ["Search"] and f["campaigns"][0]["roas_reported"] == 2.0
    assert f["booking_quality"][1]["avg_value"] == 800.0 and f["bookings_imported"]
    assert f["stages"][4]["value"] == 4 and f["stages"][4]["change"] == 0.0
    assert client.get("/api/v1/funnel/websites/1", params={"date_from": "2026-09-10", "date_to": "2026-09-01"}).status_code == 422
    assert client.get("/api/v1/funnel/websites/99").status_code == 404


def test_website_without_account_or_bookings(client):
    f = client.get("/api/v1/funnel/websites/2").json()
    assert f["website"]["ads_account_id"] is None and f["ads_reported"] is None and not f["bookings_imported"]
    assert {"no_ads_account", "bookings_not_measured"} <= {b["code"] for b in f["bottlenecks"]}


def test_interface():
    from app.shared.db import session_scope

    with session_scope() as db:
        f = interface.website_funnel(db, 1, date.today() - timedelta(days=6), date.today())
    assert f["stages"][0]["value"] == 10000
