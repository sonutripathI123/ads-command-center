"""P11 tests. P03/P05/P21 replaced through their public interfaces; the network is never used."""
from datetime import date, timedelta
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p11_competitor_intel import analysis, interface, interpret, research, service
from app.modules.p11_competitor_intel.models import Competitor, CompetitorAnalysis, CompetitorObservation
from app.modules.p21_business_rules.interface import Rules
from app.shared.db import Base, get_engine, session_scope
from app.shared.errors import FeatureDisabled

pytestmark = pytest.mark.module("P11")
REAL_RESEARCH = research.research  # the autouse fixture patches the module attribute

HOME = """<html><head><title>Rival Limos Melbourne</title><meta name="description" content="Luxury chauffeurs"></head><body>
<h1>Melbourne's Premium Chauffeur Service</h1><h2>Airport transfers</h2><h2>Wedding cars</h2>
<a href="/book">Book now</a><a href="mailto:a@b.c">a@b.c</a><a href="/book">BOOK NOW</a><a href="/q">rival.com.au/quote</a><p>Fixed price airport transfers from $95. 20 years experience. Read our reviews.
Serving Melbourne, Geelong and the Yarra Valley.</p></body></html>"""
WEDDING = "<html><head><title>Wedding Cars Melbourne | Rival</title></head><body><h1>Wedding Car Hire</h1><p>Wedding limo packages.</p></body></html>"
SITEMAP = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://rival.com.au/</loc></url><url><loc>https://rival.com.au/wedding-cars/</loc></url>
<url><loc>https://rival.com.au/private/secret</loc></url><url><loc>https://rival.com.au/tag/news</loc></url>
<url><loc>https://other.com/x</loc></url><url><loc>https://rival.com.au/about-us</loc></url></urlset>"""


def _transport():
    def handler(req):
        path = req.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\nSitemap: https://rival.com.au/sitemap.xml")
        if path == "/sitemap.xml":
            return httpx.Response(200, text=SITEMAP, headers={"content-type": "application/xml"})
        body = {"/": HOME, "/wedding-cars/": WEDDING}.get(path, "<html><title>About</title><body><h1>About us</h1></body></html>")
        return httpx.Response(200, text=body, headers={"content-type": "text/html"})
    return lambda: httpx.Client(transport=httpx.MockTransport(handler))


# ---- pure ---------------------------------------------------------------------------------------------

def test_research_honours_robots_and_prefers_service_pages():
    pages, notes = REAL_RESEARCH("https://rival.com.au/", ["wedding car", "airport transfer"], delay=0, http_factory=_transport())
    urls = [p.url for p in pages]
    assert urls == ["https://rival.com.au/", "https://rival.com.au/wedding-cars/", "https://rival.com.au/about-us"]
    home = pages[0]
    assert home.h1 == ["Melbourne's Premium Chauffeur Service"] and home.ctas == ["Book now"] and home.prices == ["from $95"]
    assert {"reviews", "experience", "fixed_price"} <= set(home.trust) and not notes


def test_research_blocked_by_robots():
    blocked = lambda: httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="User-agent: *\nDisallow: /")))  # noqa: E731
    pages, notes = REAL_RESEARCH("https://rival.com.au/", [], delay=0, http_factory=blocked)
    assert pages == [] and "robots.txt" in notes[0]


def test_profiles_coverage_gaps_and_demand():
    svc, loc = ["airport transfer", "wedding car", "cruise transfer"], ["melbourne", "geelong", "yarra valley"]
    pages = [research.parse("https://rival.com.au/", 200, HOME).to_dict(), research.parse("https://rival.com.au/wedding-cars", 200, WEDDING).to_dict()]
    profs = [analysis.page_profile(p, svc, loc) for p in pages]
    assert {"airport transfer", "wedding car", "geelong", "yarra valley"} <= profs[0]["mentions"]
    assert profs[1]["dedicated"] >= {"wedding car", "melbourne"} and profs[1]["themes"] == ["wedding", "limo"] or "wedding" in profs[1]["themes"]
    ours = [{"mentions": {"airport transfer", "cruise transfer"}, "dedicated": {"airport transfer", "cruise transfer"}, "themes": []}]
    rows = analysis.coverage(ours, {1: profs}, svc + loc)
    g = analysis.gaps(rows, {1: "Rival"})
    assert [x["term"] for x in g["gaps"]] == ["wedding car", "melbourne"] and [a["term"] for a in g["advantages"]] == ["airport transfer", "cruise transfer"]  # theirs only in an H2
    port = {"url": "https://x.com.au/chauffeur-service-in-port-melbourne", "title": "", "h1": ["Chauffeur Service in Port Melbourne"]}
    assert analysis.page_profile(port, [], [])["themes"] == []  # "port" alone is not a cruise page
    assert research.choose_pages(["https://x.com.au/the-ultimate-guide-to-airport-transfer-and-wedding-car-tips", "https://x.com.au/airport-transfer",
                                  "https://x.com.au/"], "https://x.com.au/", ["airport transfer", "wedding car", "tip"], 2) == \
        ["https://x.com.au/", "https://x.com.au/airport-transfer"]
    assert analysis.dedupe_terms(["airport transfer", "airport transfers", "Limo"]) == ["airport transfer", "limo"]
    terms = [{"search_term": "rival limos melbourne", "impressions": 50, "clicks": 3, "cost": 9.0, "conversions": 0},
             {"search_term": "RivalLimos price", "impressions": 5, "clicks": 1, "cost": 2.0, "conversions": 0},
             {"search_term": "chauffeur melbourne", "impressions": 99, "clicks": 9, "cost": 30.0, "conversions": 1}]
    d = analysis.search_demand(terms, analysis.brand_terms("Rival Limos", "rivallimos.com.au", []))
    assert d["terms"] == 2 and d["clicks"] == 4 and d["cost"] == 11.0 and d["top"][0]["search_term"] == "rival limos melbourne"
    m = analysis.messaging(pages)
    assert m["home_h1"] == ["Melbourne's Premium Chauffeur Service"] and m["prices"] == ["from $95"]


def test_interpretation_evidence_is_validated():
    i = interpret.Interpretation(summary="s", competitors=[interpret.CompetitorView(name="R", positioning="p", strengths=["x"], weaknesses=[],
                                                                                 evidence=["obs:1", "obs:999"])],
                                 opportunities=[interpret.Opportunity(title="t", why="w", action="a", channel="both", evidence=["made:up"]),
                                                interpret.Opportunity(title="t2", why="w", action="a", channel="ads", evidence=["gap:wedding car"])],
                                 messaging_angles=[], caveats=[])
    out = interpret.clean(i, {"obs:1", "gap:wedding car"})
    assert out.competitors[0].evidence == ["obs:1"] and [o.title for o in out.opportunities] == ["t2"] and "2 evidence" in out.caveats[0]
    text, keys = interpret.evidence_block([{"id": 1, "competitor_id": 5, "kind": "serp", "source": "manual: x", "observed_on": date(2026, 9, 1),
                                            "data": {"query": "limo hire", "placement": "ad", "position": 1, "text": "Book now"}}],
                                          [{"term": "wedding car", "competitors": ["R"], "our_mentions": 0}],
                                          {"R": {"terms": 1, "impressions": 5, "clicks": 1, "cost": 2.0, "conversions": 0, "top": []}}, {5: "R"})
    assert keys == {"obs:1", "gap:wedding car", "demand:R"} and "Owner saw R in Google for 'limo hire' (ad, position 1)" in text


# ---- API ----------------------------------------------------------------------------------------------

ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="CCM")
SITE = SimpleNamespace(id=1, domain="ourcars.com.au", ads_account_id=7)
OUR_PAGES = [{"url": "https://ourcars.com.au/airport-transfers", "status_code": 200, "title": "Airport Transfers", "h1": "Airport transfer Melbourne",
              "services": ["airport transfer"], "locations": ["melbourne"]},
             {"url": "https://ourcars.com.au/old", "status_code": 404, "title": "", "h1": "", "services": ["wedding car"], "locations": []}]
TERMS = [{"search_term": "rival limos", "impressions": 40, "clicks": 4, "cost": 12.0, "conversions": 0}]
FLAGS = {"on": True}


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[Competitor.__table__, CompetitorObservation.__table__, CompetitorAnalysis.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    FLAGS["on"] = True
    monkeypatch.setattr(service, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(service, "list_websites", lambda db: [SITE])
    monkeypatch.setattr(service, "website_pages", lambda db, w: OUR_PAGES)
    monkeypatch.setattr(service, "search_terms", lambda db, a, d1, d2, limit: TERMS)
    monkeypatch.setattr(service, "get_rules", lambda db, a: Rules(services=["airport transfer", "wedding car"], locations=["melbourne", "geelong"]))
    monkeypatch.setattr(service, "ai_live", lambda db: False)
    monkeypatch.setattr(service, "is_enabled", lambda key, db=None: FLAGS["on"])

    def req(key, db, module_id):
        if not FLAGS["on"]:
            raise FeatureDisabled(f"Feature '{key}' is disabled", module_id=module_id)

    monkeypatch.setattr(service, "require_enabled", req)
    real = REAL_RESEARCH
    monkeypatch.setattr(service.research, "research", lambda base, kw: real(base, kw, delay=0, http_factory=_transport()))
    yield
    with session_scope() as db:
        for t in (CompetitorAnalysis, CompetitorObservation, Competitor):
            db.execute(delete(t))


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


B = "/api/v1/competitors"


def _add(client, **kw):
    return client.post(f"{B}/accounts/7/competitors", json={"name": "Rival Limos", "website": "www.rival.com.au", "brand_terms": ["Rival"]} | kw)


def test_add_validate_and_edit(client):
    r = _add(client)
    assert r.status_code == 201 and r.json()["domain"] == "rival.com.au"
    assert _add(client).status_code == 422  # duplicate
    assert _add(client, website="ourcars.com.au").status_code == 422  # own site
    assert _add(client, website="not a site").status_code == 422
    cid = r.json()["id"]
    assert client.patch(f"{B}/competitors/{cid}", json={"status": "gone"}).status_code == 422
    assert client.patch(f"{B}/competitors/{cid}", json={"notes": "Big fleet", "brand_terms": ["RIVAL", "rival limo"]}).status_code == 200
    ov = client.get(f"{B}/accounts/7").json()
    c = ov["competitors"][0]
    assert c["notes"] == "Big fleet" and c["brand_terms"] == ["rival", "rival limo"] and c["pages_read"] == 0
    assert c["search_demand"]["clicks"] == 4 and ov["analysis"] is None and ov["our_pages"] == 1  # 404 page skipped
    client.patch(f"{B}/competitors/{cid}", json={"status": "archived"})
    assert client.get(f"{B}/accounts/7").json()["competitors"] == []
    again = _add(client, website="https://www.rival.com.au/", brand_terms=[])  # re-adding an archived one restores it
    assert again.status_code == 201 and again.json()["id"] == cid
    assert client.get(f"{B}/accounts/7").json()["competitors"][0]["brand_terms"] == ["rival", "rival limo"]


def test_research_coverage_gaps_and_history(client):
    cid = _add(client).json()["id"]
    r = client.post(f"{B}/competitors/{cid}/research")
    assert r.status_code == 200 and r.json()["pages_read"] == 3
    ov = client.get(f"{B}/accounts/7").json()
    c = ov["competitors"][0]
    assert c["pages_read"] == 3 and c["messaging"]["prices"] == ["from $95"] and "wedding" in c["themes"]
    assert c["last_researched_at"].endswith(("+00:00", "Z"))
    gaps = {g["term"] for g in ov["gaps"]["services"]["gaps"]}
    assert gaps == {"wedding car"} and [a["term"] for a in ov["gaps"]["services"]["advantages"]] == ["airport transfer"]
    svc = {row["term"]: row for row in ov["coverage"]["services"]}
    assert svc["airport transfer"]["us"] == {"pages": 1, "dedicated": 1} and svc["wedding car"]["competitors"][str(cid)]["dedicated"] == 1
    client.post(f"{B}/competitors/{cid}/research")  # re-run: old page rows kept but not current
    assert len(client.get(f"{B}/competitors/{cid}/pages").json()) == 3
    with session_scope() as db:
        assert len(service.observations(db, [cid], current_only=False)) == 6
    assert "text" not in client.get(f"{B}/competitors/{cid}/pages").json()[0]["data"]


def test_manual_observations(client):
    cid = _add(client).json()["id"]
    ok = client.post(f"{B}/competitors/{cid}/observations", json={"kind": "serp", "query": "limo hire melbourne", "placement": "ad",
                                                                   "position": 1, "text": "Rival — Book Online"})
    assert ok.status_code == 201
    bad = [{"kind": "serp", "placement": "ad"}, {"kind": "serp", "query": "x", "placement": "tv"},
           {"kind": "serp", "query": "x", "placement": "ad", "position": 99}, {"kind": "note"}, {"kind": "spy"},
           {"kind": "note", "text": "x", "observed_on": str(date.today() + timedelta(days=2))}]
    for b in bad:
        assert client.post(f"{B}/competitors/{cid}/observations", json=b).status_code == 422, b
    client.post(f"{B}/competitors/{cid}/observations", json={"kind": "note", "text": "Runs radio ads"})
    obs = client.get(f"{B}/accounts/7").json()["competitors"][0]["observations"]
    assert [o["kind"] for o in obs] == ["note", "serp"] or {o["kind"] for o in obs} == {"note", "serp"}
    assert client.delete(f"{B}/observations/{ok.json()['id']}").status_code == 204
    client.post(f"{B}/competitors/{cid}/research")
    page_id = client.get(f"{B}/competitors/{cid}/pages").json()[0]["id"]
    assert client.delete(f"{B}/observations/{page_id}").status_code == 422
    assert client.delete(f"{B}/observations/999999").status_code == 404


def test_analyze_template_live_and_failure(client, monkeypatch):
    assert client.post(f"{B}/accounts/7/analyze", json={}).status_code == 422  # no competitors
    cid = _add(client).json()["id"]
    client.post(f"{B}/competitors/{cid}/research")
    r = client.post(f"{B}/accounts/7/analyze", json={"use_ai": True})
    assert r.status_code == 201 and r.json()["mode"] == "template"
    opps = r.json()["interpretation"]["opportunities"]
    assert opps[0]["evidence"] == ["gap:wedding car"] and any(o["evidence"] == ["demand:Rival Limos"] for o in opps)
    assert r.json()["observations_used"] == 3 and client.get(f"{B}/accounts/7").json()["analysis"]["id"] == r.json()["id"]
    monkeypatch.setattr(service, "ai_live", lambda db: True)
    seen = {}

    def fake(text, keys, s):
        seen["keys"] = keys
        return interpret.template([], {}, {}), 700, "claude-opus-5"

    monkeypatch.setattr(service.interpret, "with_claude", fake)
    r = client.post(f"{B}/accounts/7/analyze", json={"use_ai": True}).json()
    assert r["mode"] == "live" and "gap:wedding car" in seen["keys"] and "demand:Rival Limos" in seen["keys"]

    def boom(text, keys, s):
        raise interpret.InterpretError("Claude declined this request")

    monkeypatch.setattr(service.interpret, "with_claude", boom)
    assert client.post(f"{B}/accounts/7/analyze", json={"use_ai": True}).status_code == 502
    with session_scope() as db:
        s = interface.competitor_summary(db, 7)
    assert s["competitors"] == ["Rival Limos"] and s["service_gaps"] == ["wedding car"] and s["opportunities"] == []  # latest = fake live run


def test_flag_and_permissions(client, app):
    cid = _add(client).json()["id"]
    FLAGS["on"] = False
    assert client.post(f"{B}/competitors/{cid}/research").status_code == 409
    assert client.get(f"{B}/accounts/7").json()["research_enabled"] is False
    assert client.post(f"{B}/competitors/{cid}/observations", json={"kind": "note", "text": "manual still works"}).status_code == 201
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert _add(client, website="x2.com.au").status_code == 403 and client.post(f"{B}/competitors/{cid}/research").status_code == 403
    assert client.get(f"{B}/accounts/7").status_code == 200 and client.get(f"{B}/accounts/99").status_code == 404
