"""P15 tests. Other modules replaced through their public interfaces."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p15_campaign_builder import builder, router, service
from app.modules.p15_campaign_builder.models import CampaignDraft
from app.modules.p21_business_rules.interface import Rules
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P15")


def kw(text, cost=5.0, clicks=2, conv=0.0, ag="1", status="ENABLED"):
    return {"text": text, "cost": cost, "clicks": clicks, "conversions": conv, "impressions": clicks * 10,
            "ad_group_google_id": ag, "ad_group_name": "Ad group 1", "status": status}


KWS = [kw("melbourne airport transfer", 40, 12, 2), kw("airport chauffeur melbourne"), kw("corporate chauffeur melbourne", conv=1),
       kw("executive car service"), kw("wedding car hire melbourne"), kw("limousine hire melbourne"), kw("stretch limo"),
       kw("europcar car hire"), kw("chauffeur jobs melbourne"), kw("private driver melbourne"), kw("xyz thing"),
       kw("melbourne airport transfer")]  # duplicate


@pytest.mark.parametrize("text,theme", [("melbourne airport transfer", "airport"), ("airport limousine", "airport"),
                                        ("wedding limo", "wedding"), ("stretch limo hire", "limo"), ("corporate car hire", "corporate"),
                                        ("private driver melbourne", "chauffeur"), ("yarra valley winery tour", "tours"),
                                        ("random words", None), ("limos near me", "limo"), ("chauffeurs in melbourne", "chauffeur"),
                                        ("hire cars with drivers", "chauffeur")])
def test_theme_of(text, theme):
    assert builder.theme_of(text) == theme


def test_cluster_splits_themes_negatives_and_dedupes():
    values = {"chauffeur jobs melbourne": "negative"}
    groups, unassigned, negs = builder.cluster(KWS, values)
    assert set(groups) == {"airport", "corporate", "wedding", "limo", "chauffeur"}
    assert [k.text for k in groups["airport"]] == ["melbourne airport transfer", "airport chauffeur melbourne"]
    assert groups["airport"][0].match_type == "EXACT" and groups["airport"][1].match_type == "PHRASE"
    assert [k.text for k in unassigned] == ["xyz thing"]
    assert {n["text"] for n in negs} == {"europcar", "chauffeur jobs melbourne"}
    groups2, _, _ = builder.cluster(KWS, values, themes=["airport"])
    assert set(groups2) == {"airport"}


def test_best_landing_page():
    pages = [{"url": "https://x.com.au/", "title": "Home", "h1": "", "issues": [], "status_code": 200, "cta_count": 2, "has_form": True},
             {"url": "https://x.com.au/airport-transfers", "title": "Airport Transfers Melbourne", "h1": "Airport", "issues": [],
              "status_code": 200, "cta_count": 3, "has_form": True},
             {"url": "https://x.com.au/airport-old", "title": "Airport", "h1": "", "issues": ["http_error"], "status_code": 404}]
    url, score, why = builder.best_landing_page("airport", pages, "https://x.com.au")
    assert url.endswith("/airport-transfers") and score >= 75 and "URL" in why
    assert builder.best_landing_page("wedding", pages, "https://x.com.au")[0] == "https://x.com.au/"
    niche = [{"url": "https://x.com.au/car-service-with-baby-seat", "title": "Car Service", "h1": "", "issues": [], "status_code": 200}]
    assert builder.best_landing_page("chauffeur", niche, "https://x.com.au")[0] == "https://x.com.au/"  # generic → homepage


def test_settings_follow_tracking_health():
    bad = builder.default_settings(daily_budget=30, max_cpc=3, tracking_ok=False, locations=["melbourne"])
    assert bad["status"] == "PAUSED" and bad["bidding"] == {"strategy": "MAXIMIZE_CLICKS", "max_cpc": 3}
    assert bad["networks"] == {"google_search": True, "search_partners": False, "display": False}
    assert builder.default_settings(daily_budget=30, max_cpc=3, tracking_ok=True, locations=[])["bidding"]["strategy"] == "MAXIMIZE_CONVERSIONS"


# ---- API ----------------------------------------------------------------------------------------------

ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="")
SITE = SimpleNamespace(id=1, name="CCM", domain="x.com.au", base_url="https://x.com.au", location="Melbourne", ads_account_id=7)
ADS: dict[int, dict] = {}


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[CampaignDraft.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    ADS.clear()
    monkeypatch.setattr(service, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(router, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(router, "list_websites", lambda db: [SITE])
    monkeypatch.setattr(router, "keywords", lambda db, a, d1, d2: KWS)
    monkeypatch.setattr(router, "ad_groups", lambda db, a, d1, d2: [{"google_id": "1", "name": "Ad group 1", "campaign_name": "C", "status": "ENABLED"}])
    monkeypatch.setattr(service, "ads_keywords", lambda db, a, d1, d2: KWS)
    monkeypatch.setattr(service, "classify_terms", lambda db, a, t: {x: ("i", "negative" if "jobs" in x else "high", []) for x in t})
    monkeypatch.setattr(service, "get_rules", lambda db, a: Rules(excluded_terms=["jobs", "uber"], other_locations=["sydney"], locations=["melbourne"]))
    monkeypatch.setattr(service, "list_websites", lambda db: [SITE])
    monkeypatch.setattr(service, "website_pages", lambda db, w: [])
    monkeypatch.setattr(service, "landing_pages", lambda db, w: [])
    monkeypatch.setattr(service, "tracking_health", lambda db, w, d1, d2: [{"severity": "critical", "title": "GA4 records no conversions"}])
    monkeypatch.setattr(service, "accepted_negatives", lambda db, a: [{"text": "didi", "match_type": "PHRASE"}])

    def write_rsa(db, account_id, **kw):
        i = len(ADS) + 1
        ADS[i] = {"id": i, "status": "draft", "strength": 100, "headlines": ["H1", "H2", "H3"], "descriptions": ["D1", "D2"],
                  "path1": "p", "path2": "q", "final_url": kw["final_url"], "_kw": kw}
        return ADS[i]

    monkeypatch.setattr(service, "write_rsa", write_rsa)
    monkeypatch.setattr(service, "get_ad_draft", lambda db, i: ADS.get(i))
    yield
    with session_scope() as db:
        db.execute(delete(CampaignDraft))


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


B = "/api/v1/campaign-builder"


def _build(client, **kw):
    return client.post(f"{B}/accounts/7/drafts", json={"name": "CCM | Search | Restructure", "source_ad_groups": ["1"], "daily_budget": 25} | kw)


def test_build_draft(client):
    r = _build(client)
    assert r.status_code == 201, r.text
    d = r.json()
    assert [g["key"] for g in d["ad_groups"]] == ["airport", "wedding", "limo", "corporate", "chauffeur"]
    assert d["ad_groups"][0]["name"] == "Airport Transfers Melbourne" and d["ad_groups"][0]["final_url"] == "https://x.com.au/"
    assert {"europcar", "chauffeur jobs melbourne", "jobs", "uber", "sydney", "didi"} <= {n["text"] for n in d["negatives"]}
    assert d["settings"]["status"] == "PAUSED" and d["settings"]["bidding"]["strategy"] == "MAXIMIZE_CLICKS"
    items = {i["key"]: i["status"] for i in d["checklist"]}
    assert items["tracking"] == "fail" and items["ads"] == "fail" and items["negatives"] == "pass" and items["location"] == "manual"
    assert [k["text"] for k in d["unassigned"]] == ["xyz thing"]


def test_edit_ops(client):
    d = _build(client).json()
    did = d["id"]
    client.patch(f"{B}/drafts/{did}", json={"op": "move_keyword", "text": "xyz thing", "from": "unassigned", "to": "chauffeur"})
    client.patch(f"{B}/drafts/{did}", json={"op": "remove_keyword", "text": "stretch limo", "from": "limo"})
    client.patch(f"{B}/drafts/{did}", json={"op": "rename_group", "group": "limo", "name": "Limo Hire"})
    client.patch(f"{B}/drafts/{did}", json={"op": "add_negative", "text": "Bus"})
    client.patch(f"{B}/drafts/{did}", json={"op": "remove_negative", "text": "sydney"})
    r = client.patch(f"{B}/drafts/{did}", json={"op": "settings", "daily_budget": 40, "max_cpc": 3.5}).json()
    g = {x["key"]: x for x in r["ad_groups"]}
    assert "xyz thing" in [k["text"] for k in g["chauffeur"]["keywords"]] and not r["unassigned"]
    assert [k["text"] for k in g["limo"]["keywords"]] == ["limousine hire melbourne"] and g["limo"]["name"] == "Limo Hire"
    negs = {n["text"] for n in r["negatives"]}
    assert "bus" in negs and "sydney" not in negs
    assert r["settings"]["daily_budget"] == 40 and r["settings"]["bidding"]["max_cpc"] == 3.5
    assert client.patch(f"{B}/drafts/{did}", json={"op": "nope"}).status_code == 422


def test_write_ads_approve_and_export(client):
    d = _build(client).json()
    did = d["id"]
    assert client.patch(f"{B}/drafts/{did}", json={"op": "status", "status": "approved"}).status_code == 422  # ads missing
    for g in d["ad_groups"]:
        r = client.post(f"{B}/drafts/{did}/ad-groups/{g['key']}/write-ads", json={"usps": ["Fixed price"]})
        assert r.status_code == 200
    assert ADS[1]["_kw"]["usps"] == ["Fixed price"] and ADS[1]["_kw"]["campaign_name"] == "CCM | Search | Restructure"
    assert client.patch(f"{B}/drafts/{did}", json={"op": "status", "status": "approved"}).status_code == 422  # ads not approved
    for a in ADS.values():
        a["status"] = "approved"
    r = client.patch(f"{B}/drafts/{did}", json={"op": "status", "status": "approved"})
    assert r.status_code == 200 and r.json()["status"] == "approved"  # tracking fail does not block (stays paused)
    assert client.patch(f"{B}/drafts/{did}", json={"op": "rename", "name": "x"}).status_code == 422  # locked when approved
    csv = client.get(f"{B}/drafts/{did}/export").text.splitlines()
    assert csv[0].startswith("Campaign,Campaign Type,Campaign Status")
    body = "\n".join(csv)
    assert "Search,Paused,25.0,Maximize clicks" in body and "Negative Phrase" in body and "Responsive search ad" in body
    assert body.count("Paused") >= 1 + len(d["ad_groups"])


def test_export_requires_approval_and_permissions(client, app):
    did = _build(client).json()["id"]
    assert client.get(f"{B}/drafts/{did}/export").status_code == 422
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ, Permission.RECOMMEND})
    assert client.patch(f"{B}/drafts/{did}", json={"op": "status", "status": "approved"}).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert _build(client).status_code == 403
    assert client.get(f"{B}/drafts/{did}").status_code == 200


def test_validation(client):
    assert _build(client, themes=["space"]).status_code == 422
    assert _build(client, source_ad_groups=["nope"]).status_code == 422
    accs = client.get(f"{B}/accounts").json()
    assert accs[0]["websites"][0]["id"] == 1 and len(accs[0]["themes"]) == len(builder.THEMES)
    assert accs[0]["ad_groups"][0]["keywords"] == len(KWS)


def test_rental_with_driver_is_kept_but_jobs_are_negated():
    rows = [kw("chauffeur driven car rental"), kw("chauffeur jobs melbourne"), kw("chauffeured cars melbourne")]
    values = {"chauffeur driven car rental": "negative", "chauffeur jobs melbourne": "negative"}
    groups, unassigned, negs = builder.cluster(rows, values)
    assert {k.text for k in groups["chauffeur"]} == {"chauffeur driven car rental", "chauffeured cars melbourne"}
    assert [n["text"] for n in negs] == ["chauffeur jobs melbourne"] and not unassigned
