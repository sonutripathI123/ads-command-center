"""P07 tests: pure checks + API (other modules replaced through their public interfaces)."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p07_ppc_audit import router, service
from app.modules.p07_ppc_audit.checks import AuditData, run_checks, score
from app.modules.p07_ppc_audit.models import AuditIssue, AuditRun
from app.modules.p21_business_rules.interface import Rules
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P07")


def M(cost=0.0, clicks=0, conv=0.0, impr=None):
    return {"cost": cost, "clicks": clicks, "impressions": impr if impr is not None else clicks * 10, "conversions": conv,
            "ctr": 0.1 if clicks else None, "cost_per_conversion": cost / conv if conv else None, "conv_rate": conv / clicks if clicks else None}


SITE = SimpleNamespace(id=1, name="Corporate Cars Melbourne", domain="corporatecarsmelbourne.com.au", ads_account_id=7)


def data(**kw) -> AuditData:
    base = dict(
        currency="AUD", days=90, totals=M(1500, 600, 5),
        campaigns=[{"google_id": "1", "name": "Search A", "status": "PAUSED", "bidding_strategy_type": "MAXIMIZE_CONVERSIONS", **M(900, 350, 5)},
                   {"google_id": "2", "name": "Search B", "status": "PAUSED", "bidding_strategy_type": "MANUAL_CPC", **M(600, 250, 0)}],
        ad_groups=[{"google_id": "10", "name": "Airport", "status": "ENABLED", "type": "SEARCH_STANDARD", **M()},
                   {"google_id": "11", "name": "Empty", "status": "ENABLED", "type": "SEARCH_STANDARD", **M()}],
        keywords=[{"text": f"kw{i}", "match_type": "BROAD", "status": "ENABLED", "quality_score": 3, "campaign_google_id": "1",
                   "campaign_name": "Search A", "ad_group_name": "Airport", **M(40, 10)} for i in range(6)],
        search_terms=[{"search_term": "uber melbourne", **M(30, 8)}, {"search_term": "airport transfer melbourne", **M(200, 60)}],
        ads=[{"status": "ENABLED", "type": "RESPONSIVE_SEARCH_AD", "ad_group_name": "Airport", "headlines": ["a"] * 5, "descriptions": ["b"] * 2}],
        term_values={"uber melbourne": "negative", "airport transfer melbourne": "high"}, rules=Rules(), website=SITE,
        tracking=[{"code": "no_key_events", "title": "GA4 records no conversions", "detail": "380 sessions, 0 key events"},
                  {"code": "ga4_started_late", "title": "late", "detail": "x"}],
        landing_pages=[{"final_url": "https://corporatecarsmelbourne.com.au/x", "status": "broken", "page_id": 5, "ads": 2, "ad_groups": ["A › Airport"]},
                       {"final_url": "https://www.opalchauffeurs.com.au/", "status": "other_domain", "page_id": None, "ads": 1, "ad_groups": ["A › G1"]},
                       {"final_url": "https://corporatecarsmelbourne.com.au/ok", "status": "ok", "page_id": 6, "ads": 3, "ad_groups": ["A › Airport"]}],
        pages=[{"id": 6, "url": "https://corporatecarsmelbourne.com.au/ok", "issues": ["no_cta", "slow"]}],
        organic_queries=[{"query": "corporate cars melbourne", "position": 16.9, "impressions": 195, "clicks": 3}])
    base.update(kw)
    return AuditData(**base)


def codes(issues):
    return [i.code for i in issues]


def test_full_audit_finds_expected_issues_and_orders_by_severity():
    issues = run_checks(data())
    c = codes(issues)
    for expected in ["all_campaigns_paused", "tracking_no_key_events", "smart_bidding_on_weak_data", "landing_page_broken",
                     "campaign_no_conversions", "irrelevant_search_spend", "broad_match_no_conversions", "low_quality_score",
                     "ad_groups_without_ads", "thin_responsive_ads", "landing_page_other_domain", "landing_page_weak",
                     "brand_ranks_poorly", "low_conversion_rate"]:
        assert expected in c, expected
    assert "tracking_ga4_started_late" not in c  # informational P06 item is not re-raised
    sev = [i.severity for i in issues]
    assert sev == sorted(sev, key=["critical", "warning", "info"].index)
    assert 0 <= score(issues) < 50


def test_every_issue_has_contract_fields():
    for i in run_checks(data()):
        assert i.title and i.observation and i.reasoning and i.action and i.impact
        assert 0 < i.confidence <= 1 and i.risk in ("low", "medium", "high")


def test_healthy_account_scores_high():
    healthy = data(
        totals=M(1000, 400, 40),
        campaigns=[{"google_id": "1", "name": "A", "status": "ENABLED", "bidding_strategy_type": "MAXIMIZE_CONVERSIONS", **M(1000, 400, 40)}],
        ad_groups=[{"google_id": "10", "name": "Airport", "status": "ENABLED", "type": "SEARCH_STANDARD", **M()}],
        keywords=[{"text": "airport transfer", "match_type": "PHRASE", "status": "ENABLED", "quality_score": 8, "campaign_google_id": "1",
                   "campaign_name": "A", "ad_group_name": "Airport", **M(1000, 400, 40)}],
        search_terms=[{"search_term": "airport transfer melbourne", **M(1000, 400, 40)}],
        ads=[{"status": "ENABLED", "type": "RESPONSIVE_SEARCH_AD", "ad_group_name": "Airport", "headlines": ["h"] * 12, "descriptions": ["d"] * 4}],
        tracking=[], landing_pages=[{"final_url": "https://x/ok", "status": "ok", "page_id": 6, "ads": 1, "ad_groups": []}],
        pages=[{"id": 6, "url": "https://x/ok", "issues": []}], organic_queries=[{"query": "corporate cars melbourne", "position": 1.5, "impressions": 100, "clicks": 40}])
    assert run_checks(healthy) == [] and score([]) == 100


def test_target_cpa_and_no_website():
    issues = run_checks(data(rules=Rules(target_cost_per_conversion=50), website=None, landing_pages=[], pages=[]))
    c = codes(issues)
    assert "campaign_above_target_cpa" in c and "no_website_linked" in c  # Search A: 180/conv vs 50


# ---- API ----------------------------------------------------------------------------------------

ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="", currency_code="AUD")


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[AuditRun.__table__, AuditIssue.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    d = data()
    monkeypatch.setattr(service.ads, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(router, "list_accounts", lambda db: [ACC])
    for name, val in [("summary", {"totals": d.totals}), ("campaigns", d.campaigns), ("ad_groups", d.ad_groups),
                      ("keywords", d.keywords), ("ads", d.ads)]:
        monkeypatch.setattr(service.ads, name, lambda db, a, d1, d2, _v=val: _v)
    monkeypatch.setattr(service.ads, "search_terms", lambda db, a, d1, d2, limit=500: d.search_terms)
    monkeypatch.setattr(service, "classify_terms", lambda db, a, terms: {t: ("x", d.term_values.get(t, "unknown"), []) for t in terms})
    monkeypatch.setattr(service, "list_websites", lambda db: [SITE])
    monkeypatch.setattr(service, "website_overview", lambda db, w, d1, d2: {"health": d.tracking, "top_queries": d.organic_queries})
    monkeypatch.setattr(service, "landing_pages", lambda db, w: d.landing_pages)
    monkeypatch.setattr(service, "website_pages", lambda db, w: d.pages)
    monkeypatch.setattr(service, "get_rules", lambda db, a: Rules())
    yield
    with session_scope() as db:
        db.execute(delete(AuditIssue))
        db.execute(delete(AuditRun))


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


def test_run_and_latest(client):
    r = client.post("/api/v1/audit/accounts/7/run", json={"days": 90}).json()
    assert r["score"] < 50 and r["counts"]["critical"] >= 3 and r["triggered_by"] == "me@example.com"
    latest = client.get("/api/v1/audit/accounts/7/latest").json()
    first = latest["issues"][0]
    assert first["severity"] == "critical" and first["module_id"] == "P07" and first["evidence"]
    assert {"observation", "reasoning", "proposed_action", "expected_impact", "confidence", "risk"} <= set(first)
    assert client.get("/api/v1/audit/accounts").json()[0]["last_audit"]["score"] == r["score"]


def test_dismissal_sticks_across_runs(client):
    client.post("/api/v1/audit/accounts/7/run", json={})
    issue = next(i for i in client.get("/api/v1/audit/accounts/7/latest").json()["issues"] if i["code"] == "landing_page_other_domain")
    client.post(f"/api/v1/audit/issues/{issue['id']}/status", json={"status": "dismissed", "note": "Opal is our sister brand"})
    client.post("/api/v1/audit/accounts/7/run", json={})
    latest = client.get("/api/v1/audit/accounts/7/latest").json()
    assert "landing_page_other_domain" not in [i["code"] for i in latest["issues"]] and latest["dismissed"] == 1
    again = client.get("/api/v1/audit/accounts/7/latest?include_dismissed=true").json()
    d = next(i for i in again["issues"] if i["code"] == "landing_page_other_domain")
    assert d["dismiss_note"] == "Opal is our sister brand"
    assert len(client.get("/api/v1/audit/accounts/7/history").json()) == 2


def test_one_failing_source_does_not_stop_audit(client, monkeypatch):
    def boom(db, w, d1, d2):
        raise RuntimeError("GA4 down")

    monkeypatch.setattr(service, "website_overview", boom)
    r = client.post("/api/v1/audit/accounts/7/run", json={}).json()
    assert r["errors"] and "GA4 down" in r["errors"][0] and r["score"] >= 0


def test_permissions_and_validation(client, app):
    assert client.post("/api/v1/audit/accounts/99/run", json={}).status_code == 404
    assert client.post("/api/v1/audit/accounts/7/run", json={"days": 3}).status_code == 422
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert client.post("/api/v1/audit/accounts/7/run", json={}).status_code == 403
    assert client.get("/api/v1/audit/accounts/7/latest").status_code == 200


def test_huge_ad_group_is_a_warning():
    kws = [{"text": f"k{i}", "match_type": "PHRASE", "status": "ENABLED", "quality_score": 7, "campaign_google_id": "1",
            "campaign_name": "A", "ad_group_name": "Ad group 1", **M()} for i in range(120)]
    issue = next(i for i in run_checks(data(keywords=kws)) if i.code == "oversized_ad_groups")
    assert issue.severity == "warning" and "Ad group 1 (120)" in issue.observation
