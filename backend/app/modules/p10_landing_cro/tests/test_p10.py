"""P10 tests. P03/P05/P06/P21 replaced through their public interfaces; the network is never used."""
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p10_landing_cro import brief, fetch, interface, router, rules, service
from app.modules.p10_landing_cro.extract import extract
from app.modules.p10_landing_cro.models import CroFinding, ImplementationBrief, LandingPageCheck
from app.modules.p21_business_rules.interface import Rules
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P10")

GOOD = """<html><head><title>Melbourne Airport Chauffeur Transfers</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Airport chauffeur">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ABC123"></script><script>gtag('config','AW-123456789')</script>
<script type="application/ld+json">{"@type":"LocalBusiness","aggregateRating":{"@type":"AggregateRating"}}</script></head>
<body><header><a href="tel:+61390000000">Call 03 9000 0000</a><a href="/book-now">Book now</a></header>
<h1>Airport Chauffeur Transfers Melbourne</h1><h2>Corporate chauffeur service</h2>
<p>Fixed price airport transfers from $89. Licensed and insured, 15 years experience. Read our Google reviews.</p>
<form action="/quote"><input name="pickup" required><input name="dropoff"><input name="date" type="date"><input name="email" type="email">
<input type="hidden" name="src"><button type="submit">Get my quote</button></form>
<img src="a.jpg" alt="car"><p>""" + ("Serving Melbourne CBD, Toorak and Southbank with luxury sedans. " * 30) + "</p></body></html>"
BAD = "<html><head><title>Welcome</title></head><body><h1>Welcome to our site</h1><p>Hello.</p><form><input name=a>" + \
      "".join(f"<input name=f{i}>" for i in range(10)) + "<input type=submit value=Submit></form></body></html>"


# ---- pure ---------------------------------------------------------------------------------------------

def test_extract_signals():
    s = extract(GOOD)
    assert s.viewport and s.title.startswith("Melbourne Airport") and s.h1 == ["Airport Chauffeur Transfers Melbourne"]
    assert s.tel_links == 1 and s.booking_links == 1 and s.early_cta and "Book now" in s.ctas and "Get my quote" in s.ctas
    assert len(s.forms) == 1 and [f["name"] for f in s.forms[0].fields] == ["pickup", "dropoff", "date", "email"]
    assert s.forms[0].fields[0]["required"] and s.forms[0].submit_text == "Get my quote"
    assert s.trust["reviews"] and s.trust["accreditation"] and s.trust["experience"] and s.prices
    assert s.has_ga4_or_gtm and s.has_ads_tag and "LocalBusiness" in s.schema_types and s.images_without_alt == 0
    b = extract(BAD)
    assert not b.viewport and not b.ctas and len(b.forms[0].fields) == 11 and b.forms[0].submit_text == "Submit"
    assert not any(b.trust.values()) and not b.has_ga4_or_gtm


def test_coverage_is_click_weighted_and_plural_aware():
    kws = [{"text": "airport transfers melbourne", "clicks": 30}, {"text": "wedding car hire", "clicks": 10}]
    share, missing = rules.coverage(kws, "Airport transfer specialists")
    assert share == round(31 / 42, 3) and missing[0]["text"] == "wedding car hire" and missing[0]["missing"] == ["wedding"]
    assert rules.coverage([], "x") == (None, [])


CTX = {"ads": [{"headlines": ["Airport Chauffeur Melbourne", "Book Your Transfer"]}], "keywords":
       [{"text": "airport chauffeur", "clicks": 40}, {"text": "wedding limo", "clicks": 50}], "cost": 120.0, "clicks": 60, "conversions": 0}
PAGE = {"url": "https://x.com.au/", "status_code": 200, "final_url": "https://x.com.au/", "elapsed_ms": 300}


def test_rules_good_vs_bad():
    good = rules.check(PAGE, extract(GOOD).to_dict(), CTX, locations=["melbourne"], tracking_issues=[])
    codes = {f.code for f in good}
    assert "low_keyword_coverage" in codes  # wedding limo not covered (45% by clicks → warning)
    assert not codes & {"no_viewport", "no_cta", "no_booking_path", "no_analytics_tag", "no_trust", "h1_intent_mismatch"}
    assert "spend_no_conversions" in codes
    bad = rules.check(PAGE | {"elapsed_ms": 3200}, extract(BAD).to_dict(), CTX, locations=["melbourne"],
                      tracking_issues=["Form starts are tracked, but not form submissions"])
    bcodes = {f.code for f in bad}
    assert {"no_viewport", "no_cta", "no_analytics_tag", "conversions_not_tracked", "long_form", "generic_submit", "no_trust",
            "h1_intent_mismatch", "ad_message_mismatch", "no_location", "no_click_to_call", "slow_response"} <= bcodes
    assert rules.score(bad) < rules.score(good) and rules.score(bad) == 0
    unlinked = rules.check(PAGE, extract(GOOD).to_dict(), CTX, locations=["melbourne"], tracking_issues=None)
    assert "tracking_not_verified" in {f.code for f in unlinked} and "tracking_not_verified" not in codes
    faq = extract('<a href="/faq">How early should I book?</a><a href="mailto:x">book@x.com.au</a><a href="/b">Book online</a>')
    assert faq.ctas == ["Book online"]
    broken = rules.check(PAGE | {"status_code": 404}, None, CTX, locations=[], tracking_issues=[])
    assert [f.code for f in broken] == ["page_not_loading"]


def test_fetch_respects_robots_and_times():
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        return httpx.Response(200, text=GOOD, headers={"content-type": "text/html"})

    pages = fetch.fetch_pages(["https://x.com.au/", "https://x.com.au/private/p"], delay=0,
                              http_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    assert pages[0].status_code == 200 and pages[0].html and pages[0].elapsed_ms is not None
    assert pages[1].error == "Blocked by robots.txt" and pages[1].html == ""


def test_template_brief_and_markdown():
    fs = [f.to_dict() for f in rules.check(PAGE, extract(BAD).to_dict(), CTX, locations=["melbourne"], tracking_issues=["x"])]
    b = brief.template_brief("https://x.com.au/", fs, CTX, ["melbourne"])
    assert b.priority_changes[0].owner == "developer" and "tracking" in b.priority_changes[0].how.lower() or b.tracking_changes
    assert b.copy_suggestions.h1 == "Airport Chauffeur Melbourne" and len(b.priority_changes) <= 8
    md = brief.to_markdown("https://x.com.au/", b)
    assert md.startswith("# Landing page brief") and "## Tracking" in md
    text = brief.brief_input("https://x.com.au/", 10, fs, extract(BAD).to_dict(), CTX, ["melbourne"], ["airport"])
    assert "[critical/tracking]" in text and "airport chauffeur (40)" in text


# ---- API ----------------------------------------------------------------------------------------------

ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="CCM")
SITE = SimpleNamespace(id=1, domain="x.com.au", ads_account_id=7)
ADS = [{"key": "a1", "status": "ENABLED", "final_urls": ["https://www.x.com.au/"], "headlines": ["Airport Chauffeur Melbourne"],
        "campaign_name": "C", "ad_group_name": "Airport", "cost": 100.0, "clicks": 50, "conversions": 0.0},
       {"key": "a2", "status": "PAUSED", "final_urls": ["https://x.com.au"], "headlines": ["Book Now"], "campaign_name": "C",
        "ad_group_name": "Airport", "cost": 20.0, "clicks": 10, "conversions": 0.0},
       {"key": "a3", "status": "ENABLED", "final_urls": ["https://other.com.au/book"], "headlines": ["Weddings"], "campaign_name": "C",
        "ad_group_name": "Wedding", "cost": 5.0, "clicks": 2, "conversions": 0.0},
       {"key": "a4", "status": "REMOVED", "final_urls": ["https://gone.com.au/"], "headlines": [], "campaign_name": "C",
        "ad_group_name": "Old", "cost": 0.0, "clicks": 0, "conversions": 0.0}]
KWS = [{"text": "airport chauffeur", "clicks": 40, "conversions": 0, "status": "ENABLED", "campaign_name": "C", "ad_group_name": "Airport"},
       {"text": "wedding limo", "clicks": 3, "conversions": 0, "status": "ENABLED", "campaign_name": "C", "ad_group_name": "Wedding"}]
FETCHED: list[list[str]] = []


def fake_fetch(urls):
    FETCHED.append(urls)
    return [fetch.Page(u, 200, u, 250.0, GOOD) if "x.com.au" in u else fetch.Page(u, 404, u, 100.0, "") for u in urls]


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[LandingPageCheck.__table__, CroFinding.__table__, ImplementationBrief.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    FETCHED.clear()
    monkeypatch.setattr(service, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(service, "ads", lambda db, a, d1, d2: ADS)
    monkeypatch.setattr(service, "keywords", lambda db, a, d1, d2: KWS)
    monkeypatch.setattr(service, "list_websites", lambda db: [SITE])
    monkeypatch.setattr(service, "tracking_health", lambda db, w, d1, d2: [{"severity": "critical", "title": "GA4 records no conversions"}])
    monkeypatch.setattr(service, "get_rules", lambda db, a: Rules(locations=["melbourne"], services=["airport transfers"]))
    monkeypatch.setattr(service, "fetch_pages", fake_fetch)
    monkeypatch.setattr(service, "is_enabled", lambda key, db=None: key == service.FETCH_FLAG)
    monkeypatch.setattr(service, "require_enabled", lambda key, db, module_id: None)
    monkeypatch.setattr(router, "is_enabled", lambda key, db=None: key == service.FETCH_FLAG)
    yield
    with session_scope() as db:
        for t in (ImplementationBrief, CroFinding, LandingPageCheck):
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


B = "/api/v1/landing-pages"


def test_contexts_merge_urls_and_skip_removed():
    with session_scope() as db:
        ctx = service.landing_contexts(db, 7)
    assert list(ctx) == ["https://x.com.au/", "https://other.com.au/book"]
    main = ctx["https://x.com.au/"]
    assert len(main["ads"]) == 2 and main["cost"] == 120.0 and main["ad_groups"] == ["C › Airport"]
    assert [k["text"] for k in main["keywords"]] == ["airport chauffeur"]


def test_check_run_findings_and_history(client):
    r = client.post(f"{B}/accounts/7/check")
    assert r.status_code == 200, r.text
    pages = {p["url"]: p for p in r.json()["pages"]}
    assert FETCHED == [["https://www.x.com.au/", "https://other.com.au/book"]]
    broken = pages["https://other.com.au/book"]
    assert broken["score"] == 0 and [f["code"] for f in broken["findings"]] == ["page_not_loading"]
    good = pages["https://www.x.com.au/"]
    assert "conversions_not_tracked" in {f["code"] for f in good["findings"]}  # P06 issue applied to own domain only
    assert good["findings"][0]["severity"] == "critical" and good["ads"] == 2
    assert [p["url"] for p in r.json()["pages"]][0] == "https://other.com.au/book"  # worst first
    detail = client.get(f"{B}/checks/{good['id']}").json()
    assert detail["signals"]["viewport"] and "text" not in detail["signals"] and detail["context"]["keywords"]
    client.post(f"{B}/accounts/7/check")
    listing = client.get(f"{B}/accounts/7").json()
    assert len(listing["runs"]) == 2 and len(listing["pages"]) == 2
    assert listing["pages"][0]["checked_at"].endswith(("+00:00", "Z")) and listing["runs"][0]["checked_at"].endswith(("+00:00", "Z"))
    old = client.get(f"{B}/accounts/7", params={"run": listing["runs"][1]["run_key"]}).json()
    assert {p["id"] for p in old["pages"]} == {p["id"] for p in r.json()["pages"]}
    acc = client.get(f"{B}/accounts").json()
    assert acc["fetch_enabled"] and not acc["ai_live"] and acc["accounts"][0]["landing_urls"] == 2
    with session_scope() as db:
        assert {s["url"] for s in interface.landing_scores(db, 7)} == {"https://www.x.com.au/", "https://other.com.au/book"}


def test_brief_template_and_markdown(client):
    good = next(p for p in client.post(f"{B}/accounts/7/check").json()["pages"] if "x.com.au" in p["url"])
    r = client.post(f"{B}/checks/{good['id']}/brief", json={"use_ai": True})  # AI off → template
    assert r.status_code == 201 and r.json()["mode"] == "template" and r.json()["brief"]["priority_changes"]
    bid = r.json()["id"]
    assert client.get(f"{B}/checks/{good['id']}").json()["latest_brief_id"] == bid
    md = client.get(f"{B}/briefs/{bid}/markdown")
    assert md.status_code == 200 and md.text.startswith("# Landing page brief") and "attachment" in md.headers["content-disposition"]


def test_brief_live_path_and_ai_failure(client, monkeypatch):
    good = next(p for p in client.post(f"{B}/accounts/7/check").json()["pages"] if "x.com.au" in p["url"])
    monkeypatch.setattr(service, "ai_live", lambda db: True)
    b = brief.template_brief("u", [], {}, [])
    monkeypatch.setattr(service.briefs, "write_with_claude", lambda text, s: (b, 900, "claude-opus-5"))
    r = client.post(f"{B}/checks/{good['id']}/brief", json={"use_ai": True}).json()
    assert r["mode"] == "live" and r["model"] == "claude-opus-5"

    def boom(text, s):
        raise brief.BriefError("Claude declined this request")

    monkeypatch.setattr(service.briefs, "write_with_claude", boom)
    r = client.post(f"{B}/checks/{good['id']}/brief", json={"use_ai": True})
    assert r.status_code == 502 and "declined" in r.text
    assert client.post(f"{B}/checks/{good['id']}/brief", json={"use_ai": False}).json()["mode"] == "template"


def test_flag_permissions_and_errors(client, app, monkeypatch):
    from app.shared.errors import FeatureDisabled

    def off(key, db, module_id):
        raise FeatureDisabled("Feature 'crawler.enabled' is disabled", module_id=module_id)

    monkeypatch.setattr(service, "require_enabled", off)
    assert client.post(f"{B}/accounts/7/check").status_code == 409
    assert client.post(f"{B}/accounts/99/check").status_code == 404
    assert client.get(f"{B}/checks/999999").status_code == 404 and client.get(f"{B}/briefs/999999").status_code == 404
    monkeypatch.setattr(service, "ads", lambda db, a, d1, d2: [])
    monkeypatch.setattr(service, "require_enabled", lambda key, db, module_id: None)
    assert client.post(f"{B}/accounts/7/check").status_code == 404  # no ads with landing pages
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert client.post(f"{B}/accounts/7/check").status_code == 403
    assert client.get(f"{B}/accounts/7").status_code == 200
