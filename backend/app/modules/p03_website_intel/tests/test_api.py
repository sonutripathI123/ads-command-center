"""P03 API tests. P02/P05/P21 replaced via their public interfaces; the site is a MockTransport fake."""
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p03_website_intel import router, service
from app.modules.p03_website_intel.models import CrawlRun, LandingPageMapping, Page, PageSignal, Website
from app.modules.p21_business_rules.interface import Rules
from app.shared.db import Base, get_engine, session_scope
from app.shared.feature_flags import FeatureFlagOverride

from .test_extract_crawl import Site

pytestmark = pytest.mark.module("P03")
TABLES = [LandingPageMapping, PageSignal, Page, CrawlRun, Website]
ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="Corporate Cars Melbourne")
ADS = [{"key": "10~1", "final_urls": ["https://example.com.au/airport"], "campaign_name": "Search", "ad_group_name": "Airport"},
       {"key": "10~2", "final_urls": ["https://example.com.au/missing-page"], "campaign_name": "Search", "ad_group_name": "Old"},
       {"key": "10~3", "final_urls": ["https://landing.other.com/x"], "campaign_name": "Search", "ad_group_name": "LP"}]


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[t.__table__ for t in reversed(TABLES)])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    site = Site()
    monkeypatch.setattr(service, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(router, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(service, "get_rules", lambda db, a=None: Rules())
    monkeypatch.setattr(service, "ads_rows", lambda db, a, d1, d2: ADS)
    real = service.execute_crawl
    monkeypatch.setattr(service, "execute_crawl", lambda run_id: real(
        run_id, http_factory=lambda: httpx.Client(transport=httpx.MockTransport(site.handler)), delay=0, sleep=lambda s: None))
    yield site
    with session_scope() as db:
        for t in TABLES:
            db.execute(delete(t))
        db.execute(delete(FeatureFlagOverride))


def _crawler(on: bool):
    with session_scope() as db:
        db.merge(FeatureFlagOverride(key="crawler.enabled", enabled=on, reason="test"))


def _user(perms):
    return CurrentUser(id=1, email="me@example.com", name="me", role="x", permissions=frozenset(perms))


ALL = {Permission.READ, Permission.RECOMMEND, Permission.APPROVE}


@pytest.fixture
def app():
    from app.main import create_app

    a = create_app()
    a.dependency_overrides[get_current_user] = lambda: _user(ALL)
    return a


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def _add(client, **kw):
    body = {"name": "Corporate Cars Melbourne", "domain": "https://www.Example.com.au/", "primary_service": "Corporate",
            "location": "Melbourne", "ads_account_id": 7, "ga4_property_id": "550393874"} | kw
    return client.post("/api/v1/websites", json=body)


def test_create_normalises_domain_and_links_account(client):
    r = _add(client)
    assert r.status_code == 201, r.text
    w = r.json()
    assert w["domain"] == "example.com.au" and w["base_url"] == "https://www.example.com.au"
    assert w["ads_account_label"] == "Corporate Cars Melbourne" and w["pages"] == 0 and w["last_crawl"] is None


@pytest.mark.parametrize("kw,msg", [({"domain": "not a domain"}, "valid domain"), ({"ads_account_id": 99}, "Google Ads"),
                                    ({"ga4_property_id": "G-ABC123"}, "digits")])
def test_create_validation(client, kw, msg):
    r = _add(client, **kw)
    assert r.status_code == 422 and msg in r.json()["error"]["message"]


def test_duplicate_domain_rejected(client):
    _add(client)
    assert _add(client, domain="example.com.au").status_code == 422


def test_update_and_archive(client):
    wid = _add(client).json()["id"]
    r = client.patch(f"/api/v1/websites/{wid}", json={"location": "Melbourne & Geelong", "status": "archived"})
    assert r.json()["location"] == "Melbourne & Geelong"
    assert client.get("/api/v1/websites").json() == []
    assert len(client.get("/api/v1/websites?include_archived=true").json()) == 1


def test_viewer_cannot_create(client, app):
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert _add(client).status_code == 403


def test_crawl_blocked_while_flag_off(client):
    wid = _add(client).json()["id"]
    assert client.get("/api/v1/websites/meta").json()["crawler_enabled"] is False
    r = client.post(f"/api/v1/websites/{wid}/crawl", json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "feature_disabled"


def test_crawl_stores_pages_signals_and_landing_pages(client):
    _crawler(True)
    wid = _add(client).json()["id"]
    assert client.post(f"/api/v1/websites/{wid}/crawl", json={"max_pages": 10}).status_code == 202
    run = client.get(f"/api/v1/websites/{wid}/crawls").json()[0]
    assert run["status"] == "success" and run["source"] == "sitemap" and run["pages_crawled"] == 3
    pages = {p["url"]: p for p in client.get(f"/api/v1/websites/{wid}/pages").json()}
    home = pages["https://example.com.au/"]
    assert home["title"].startswith("Airport Transfers") and home["has_form"] and home["has_phone"] and home["cta_count"] >= 3
    assert "airport transfers" in home["services"] and "melbourne" in home["locations"] and home["issues"] == []
    assert "no_cta" in pages["https://example.com.au/airport"]["issues"]
    detail = client.get(f"/api/v1/websites/{wid}/pages/{home['id']}").json()
    assert detail["signals"]["schema_types"] == ["LocalBusiness", "WebSite"]
    lps = {lp["final_url"]: lp for lp in client.get(f"/api/v1/websites/{wid}/landing-pages").json()}
    assert lps["https://example.com.au/airport"]["status"] == "ok"
    assert lps["https://example.com.au/missing-page"]["status"] == "not_crawled"
    assert lps["https://landing.other.com/x"]["status"] == "other_domain"
    site = client.get(f"/api/v1/websites/{wid}").json()
    assert site["pages"] == 3 and site["pages_with_issues"] >= 1


def test_recrawl_updates_not_duplicates(client):
    _crawler(True)
    wid = _add(client).json()["id"]
    client.post(f"/api/v1/websites/{wid}/crawl", json={})
    client.post(f"/api/v1/websites/{wid}/crawl", json={})
    assert len(client.get(f"/api/v1/websites/{wid}/pages").json()) == 3
    assert len(client.get(f"/api/v1/websites/{wid}/crawls").json()) == 2


def test_unknown_website_404(client):
    assert client.get("/api/v1/websites/999").status_code == 404
    assert client.get("/api/v1/websites/999/pages").status_code == 404


def test_interface(client):
    from app.modules.p03_website_intel.interface import list_websites

    _add(client)
    with session_scope() as db:
        (w,) = list_websites(db)
    assert w.domain == "example.com.au" and w.ga4_property_id == "550393874" and w.ads_account_id == 7
