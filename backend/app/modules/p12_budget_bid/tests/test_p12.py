"""P12 tests. Google Ads is a fake read session (canned GAQL rows); P04's session opener is replaced through its interface."""
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p04_ads_connection.interface import AccountRef
from app.modules.p12_budget_bid import analysis, gaql, router, service
from app.modules.p12_budget_bid.models import SegmentFinding, SegmentRun
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P12")


def seg(key, cost, clicks, conv, **kw):
    return {"key": key, "impressions": clicks * 10, "clicks": clicks, "cost": cost, "conversions": conv, "value": conv * 70, **kw}


def data(**over):
    d = {"device": [seg("MOBILE", 600, 300, 12), seg("DESKTOP", 300, 150, 3), seg("TABLET", 100, 50, 0)],
         "day": [seg("MONDAY", 200, 100, 5), seg("TUESDAY", 200, 100, 0)], "hour": [seg(str(h), 10, 5, 0.5) for h in range(24)],
         "location": [], "campaigns": []}
    d.update(over)
    return d


def codes(findings):
    return {(f.dimension, f.segment, f.code) for f in findings}


# ---- pure analysis ----------------------------------------------------------------------------------

def test_dayparts_sum_to_total():
    parts = analysis.dayparts(data()["hour"])
    assert [p["key"][:4] for p in parts] == ["Late", "Morn", "Afte", "Even"] and sum(p["clicks"] for p in parts) == 120


def test_no_conversion_call_needs_enough_expected_conversions():
    # Tuesday: 100 clicks, 0 conversions, account converts 15/500 clicks -> expected 3.0 => flagged
    f, _ = analysis.analyse(data())
    assert ("day", "Tuesday", "no_conversions") in codes(f)
    # same shape but account converts far less -> expected < 3 -> could be luck -> NOT flagged
    d = data(device=[seg("MOBILE", 600, 300, 3), seg("DESKTOP", 300, 150, 1), seg("TABLET", 100, 50, 0)])
    f2, _ = analysis.analyse(d)
    assert ("day", "Tuesday", "no_conversions") not in codes(f2)


def test_expensive_and_efficient_segments():
    d = data(device=[seg("MOBILE", 300, 200, 10), seg("DESKTOP", 600, 200, 3), seg("TABLET", 100, 100, 5)])
    f, meta = analysis.analyse(d)
    c = codes(f)
    assert ("device", "Desktop", "expensive") in c and ("device", "Tablet", "efficient") in c
    assert meta["average_cpa"] == pytest.approx(1000 / 18)


def test_all_findings_state_confidence_and_action():
    f, _ = analysis.analyse(data())
    assert f and all(x.confidence in ("low", "medium") and x.proposed_action and x.observation for x in f)


def test_zero_conversions_overall_says_so_instead_of_blaming_segments():
    d = data(device=[seg("MOBILE", 600, 300, 0)], day=[seg("MONDAY", 200, 100, 0)])
    f, _ = analysis.analyse(d)
    assert [x.code for x in f] == ["no_conversions_at_all"]


def loc(label, canonical, cost, clicks, conv, typ="City"):
    return seg(label, cost, clicks, conv, label=label, canonical=canonical, type=typ)


def test_location_outside_country_and_not_served():
    d = data(location=[loc("Auckland CBD", "Auckland CBD,Auckland,New Zealand", 80, 20, 0), loc("Toorak", "Toorak,Victoria,Australia", 20, 10, 1)])
    f, _ = analysis.analyse(d, not_served=["auckland"])
    c = codes(f)
    assert ("location", "Outside Australia", "outside_country") in c and ("location", "Auckland CBD", "not_served") in c


def test_home_region_waste_is_softened():
    total_loc = seg("Melbourne", 400, 200, 0, label="Melbourne", canonical="Melbourne,Victoria,Australia", type="City")
    f, _ = analysis.analyse(data(location=[total_loc]))
    hit = [x for x in f if x.code == "no_conversions" and x.dimension == "location"]
    assert hit and hit[0].severity == "info" and "home region" in hit[0].proposed_action


def camp(**kw):
    return {"campaign": "C1", "status": "ENABLED", "bidding": "TARGET_SPEND", "daily_budget": 50, "cost": 300, "conversions": 6, "clicks": 120,
            "impression_share": 0.4, "lost_budget": 0.3, "lost_rank": 0.1, **kw}


def test_budget_findings():
    f = analysis.budget_findings([camp()], target_cpa=None, account_avg=60)
    assert {x.code for x in f} == {"budget_limited", "maximize_clicks"}          # CPA 50 <= 1.2 x 60 -> proven
    f = analysis.budget_findings([camp(conversions=0, cost=200, lost_rank=0.5)], None, 60)
    assert {x.code for x in f} == {"budget_limited_unproven", "rank_limited", "spend_no_conversions", "maximize_clicks"}
    assert analysis.budget_findings([camp(status="PAUSED")], None, 60) == []


# ---- pull (fake Google) ---------------------------------------------------------------------------------

def row(**seg_):
    return {"campaign": {"id": "1"}, "metrics": {"impressions": "100", "clicks": "10", "costMicros": "5000000", "conversions": 1, "conversionsValue": 70},
            "segments": seg_}


class FakeSession:
    def search(self, q):
        if "segments.device" in q:
            return [row(device="MOBILE"), row(device="MOBILE"), row(device="DESKTOP")]
        if "segments.day_of_week" in q:
            return [row(dayOfWeek="SUNDAY"), row(dayOfWeek="MONDAY")]
        if "segments.hour" in q:
            return [row(hour=9), row(hour=2)]
        if "FROM user_location_view" in q:
            return [row(geoTargetMostSpecificLocation="geoTargetConstants/1")]
        if "FROM geo_target_constant" in q:
            return [{"geoTargetConstant": {"resourceName": "geoTargetConstants/1", "name": "Toorak", "canonicalName": "Toorak,Victoria,Australia", "targetType": "Suburb"}}]
        return [{"campaign": {"name": "C1", "status": "ENABLED", "biddingStrategyType": "TARGET_SPEND"}, "campaignBudget": {"amountMicros": "50000000"},
                 "metrics": {"costMicros": "5000000", "conversions": 1, "clicks": "10", "searchImpressionShare": 0.5,
                             "searchBudgetLostImpressionShare": 0.2, "searchRankLostImpressionShare": 0.1}}]


def test_pull_aggregates_and_orders():
    d = gaql.pull(FakeSession(), date(2026, 9, 1), date(2026, 9, 30))
    mob = next(r for r in d["device"] if r["key"] == "MOBILE")
    assert mob["clicks"] == 20 and mob["cost"] == pytest.approx(10.0)
    assert [r["key"] for r in d["day"]] == ["MONDAY", "SUNDAY"] and [r["key"] for r in d["hour"]] == ["2", "9"]
    assert d["location"][0]["label"] == "Toorak" and d["campaigns"][0]["daily_budget"] == 50.0


def test_pull_only_ever_uses_select_queries():
    seen = []

    class Spy(FakeSession):
        def search(self, q):
            seen.append(q.lstrip().upper().split()[0])
            return super().search(q)

    gaql.pull(Spy(), date(2026, 9, 1), date(2026, 9, 30))
    assert seen and set(seen) == {"SELECT"}


# ---- service + API ---------------------------------------------------------------------------------------

ACC = AccountRef(id=7, customer_id="1234567890", descriptive_name="CCM", currency_code="AUD", time_zone=None, login_customer_id=None)


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[SegmentRun.__table__, SegmentFinding.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(service, "active_accounts", lambda db: [ACC])
    monkeypatch.setattr(router, "active_accounts", lambda db: [ACC])
    monkeypatch.setattr(service, "open_read_session", lambda db, a, http: FakeSession())
    monkeypatch.setattr(service, "get_rules", lambda db, a: SimpleNamespace(target_cost_per_conversion=None, other_locations=[]))
    yield
    with session_scope() as db:
        db.execute(delete(SegmentFinding))
        db.execute(delete(SegmentRun))


def test_run_stores_snapshot_and_latest_returns_it():
    with session_scope() as db:
        assert service.latest(db, 7) is None
        snap = service.run(db, 7, 30, by="me@x.com")
        assert snap["run"]["status"] == "success" and snap["tables"]["device"] and "total" in snap
        assert service.latest(db, 7)["run"]["id"] == snap["run"]["id"]


def test_failed_read_is_recorded_and_reported(monkeypatch):
    def boom(db, a, http):
        raise RuntimeError("quota")

    monkeypatch.setattr(service, "open_read_session", boom)
    with session_scope() as db:
        with pytest.raises(service.PullFailed):
            service.run(db, 7, 30, by="me")
        assert service.last_run(db, 7)["status"] == "failed" and service.latest(db, 7) is None


def test_only_latest_runs_are_kept():
    with session_scope() as db:
        for _ in range(service.KEEP_RUNS + 3):
            service.run(db, 7, 30, by="me")
        assert db.query(SegmentRun).filter_by(account_id=7).count() == service.KEEP_RUNS


def _user(perms):
    return CurrentUser(id=1, email="me@example.com", name="me", role="x", permissions=frozenset(perms))


def test_api_read_and_run_permissions():
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    c = TestClient(app, raise_server_exceptions=False)
    assert c.get("/api/v1/budget-bid/accounts").json()[0]["id"] == 7
    assert c.get("/api/v1/budget-bid/accounts/7/latest").json()["findings"] == []
    assert c.post("/api/v1/budget-bid/accounts/7/run", json={}).status_code == 403
    assert c.get("/api/v1/budget-bid/accounts/99/latest").status_code == 404
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ, Permission.RECOMMEND})
    r = c.post("/api/v1/budget-bid/accounts/7/run", json={"days": 30})
    assert r.status_code == 200 and r.json()["run"]["days"] == 30
    assert c.post("/api/v1/budget-bid/accounts/7/run", json={"days": 3}).status_code == 422
