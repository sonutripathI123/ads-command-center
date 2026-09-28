"""P08 API tests. P05/P21/P02 are replaced through their public interfaces (monkeypatch / dependency override)."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p08_keyword_intel import service
from app.modules.p08_keyword_intel.models import KeywordCandidate, NegativeKeywordCandidate, SearchTermClassification
from app.modules.p21_business_rules.interface import Rules
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P08")
B = "/api/v1/keywords/accounts/7"
TABLES = [SearchTermClassification, NegativeKeywordCandidate, KeywordCandidate]


def _t(t, cost, clicks, conv=0.0, camp="100"):
    return {"key": f"10~{t}", "search_term": t, "status": "NONE", "campaign_google_id": camp, "ad_group_google_id": "10",
            "cost": cost, "clicks": clicks, "impressions": clicks * 10, "conversions": conv, "campaign_name": "Search"}


DATA = {"terms": [_t("uber melbourne airport", 12, 6), _t("chauffeur jobs melbourne", 9, 4),
                  _t("airport transfer melbourne", 80, 30, conv=3), _t("xyz random thing", 40, 12),
                  _t("luxury car hire melbourne", 15, 4, conv=1)],
        "keywords": [{"key": "10~1", "text": "airport transfer", "match_type": "PHRASE", "status": "ENABLED", "quality_score": 7,
                      "impressions": 300, "clicks": 30, "cost": 80, "conversions": 3, "cost_per_conversion": 26.7,
                      "ad_group_name": "Airport", "campaign_name": "Search", "ad_group_google_id": "10", "campaign_google_id": "100"}]}


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[t.__table__ for t in TABLES])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(service, "list_accounts", lambda db: [SimpleNamespace(id=7)])
    monkeypatch.setattr(service, "search_terms", lambda db, a, d1, d2, limit=500: [dict(t) for t in DATA["terms"]])
    monkeypatch.setattr(service, "keywords", lambda db, a, d1, d2: [dict(k) for k in DATA["keywords"]])
    monkeypatch.setattr(service, "campaigns", lambda db, a, d1, d2: [{"google_id": "100", "name": "Search", "status": "ENABLED"}])
    monkeypatch.setattr(service, "get_rules", lambda db, a: Rules())
    yield
    with session_scope() as db:
        for t in TABLES:
            db.execute(delete(t))


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


def test_analyze_summary(client):
    r = client.post(f"{B}/analyze?days=30").json()
    assert r["search_terms"] == 5 and r["intents"]["excluded"] == 2
    assert r["negative_candidates"] >= 3 and r["high_confidence_waste"] == 21.0
    assert r["expansion_candidates"] == 2  # both converting terms are not keywords yet


def test_negatives_listed_by_confidence_and_filterable(client):
    client.post(f"{B}/analyze")
    rows = client.get(f"{B}/negatives").json()
    assert rows[0]["confidence"] >= rows[-1]["confidence"]
    assert {"uber", "jobs"} <= {r["text"] for r in rows}
    exact = next(r for r in rows if r["match_type"] == "EXACT")
    assert exact["text"] == "xyz random thing" and exact["campaign_name"] == "Search" and exact["level"] == "campaign"
    high = client.get(f"{B}/negatives?min_confidence=0.9").json()
    assert high and all(r["confidence"] >= 0.9 for r in high)


def test_review_persists_across_reanalysis_and_export(client):
    client.post(f"{B}/analyze")
    uber = next(r for r in client.get(f"{B}/negatives").json() if r["text"] == "uber")
    assert client.post(f"{B}/negatives/review", json={"ids": [uber["id"]], "status": "accepted"}).json() == {"updated": 1}
    client.post(f"{B}/analyze")
    again = next(r for r in client.get(f"{B}/negatives").json() if r["text"] == "uber")
    assert again["status"] == "accepted" and again["reviewed_by"] == "me@example.com"
    assert client.get(f"{B}/negatives/export?fmt=text").text.strip() == '"uber"'
    csv = client.get(f"{B}/negatives/export?fmt=csv")
    assert "Negative Phrase" in csv.text and "attachment" in csv.headers["content-disposition"]


def test_candidates_no_longer_found_become_stale(client):
    client.post(f"{B}/analyze")
    DATA["terms"], saved = [t for t in DATA["terms"] if "uber" not in t["search_term"]], DATA["terms"]
    try:
        client.post(f"{B}/analyze")
        assert "uber" not in {r["text"] for r in client.get(f"{B}/negatives").json()}
        assert "uber" in {r["text"] for r in client.get(f"{B}/negatives?status=stale").json()}
    finally:
        DATA["terms"] = saved


def test_bad_review_status(client):
    assert client.post(f"{B}/negatives/review", json={"ids": [1], "status": "applied"}).status_code == 422


def test_viewer_cannot_analyze_or_review(client, app):
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert client.post(f"{B}/analyze").status_code == 403
    assert client.post(f"{B}/negatives/review", json={"ids": [1], "status": "accepted"}).status_code == 403
    assert client.get(f"{B}/negatives").status_code == 200


def test_classifications_and_insights(client):
    client.post(f"{B}/analyze")
    ex = client.get(f"{B}/classifications?intent=excluded").json()
    assert {r["search_term"] for r in ex} == {"uber melbourne airport", "chauffeur jobs melbourne"}
    ins = client.get(f"{B}/insights").json()
    assert set(ins) == {"wasters", "winners", "low_quality_score", "idle", "duplicates", "expansion_candidates", "enabled_campaigns"}


def test_unknown_account(client):
    assert client.post("/api/v1/keywords/accounts/99/analyze").status_code == 404
