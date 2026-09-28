"""P06 tests. Google is a MockTransport fake; P02/P03/P05 are replaced through their public interfaces."""
import base64
import json
from datetime import date, timedelta
from urllib.parse import parse_qs

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p03_website_intel.interface import WebsiteRef
from app.modules.p06_analytics import router, service
from app.modules.p06_analytics.adapters.google import GA4Client, SearchConsoleClient, ServiceAccount
from app.modules.p06_analytics.models import (
    AnalyticsDaily, AnalyticsSyncRun, Booking, ConversionEvent, ConversionMapping, SearchConsoleDaily,
)
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P06")
TABLES = [AnalyticsDaily, ConversionEvent, SearchConsoleDaily, ConversionMapping, AnalyticsSyncRun, Booking]
TODAY = date.today()
Y = TODAY - timedelta(days=1)
LATE = Y - timedelta(days=10)  # GA4 "installed" 10 days ago


def _g(d: date) -> str:
    return d.strftime("%Y%m%d")


class FakeGoogle:
    def __init__(self):
        self.jwt_claims = None
        self.fail_gsc = False

    def handler(self, req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if url.startswith("https://oauth2.googleapis.com/token"):
            form = parse_qs(req.content.decode())
            assert form["grant_type"] == ["urn:ietf:params:oauth:grant-type:jwt-bearer"]
            payload = form["assertion"][0].split(".")[1]
            self.jwt_claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            return httpx.Response(200, json={"access_token": "sa-token", "expires_in": 3600})
        assert req.headers["authorization"] == "Bearer sa-token"
        if "analyticsdata" in url:
            body = json.loads(req.content)
            dims = [d["name"] for d in body["dimensions"]]
            if dims == ["date", "sessionDefaultChannelGroup"]:
                rows = [(LATE + timedelta(days=i), ch, s) for i in range(10) for ch, s in (("Paid Search", 5), ("Direct", 3))]
                return httpx.Response(200, json={"rowCount": len(rows), "rows": [
                    {"dimensionValues": [{"value": _g(d)}, {"value": ch}],
                     "metricValues": [{"value": str(s)}, {"value": str(s - 1)}, {"value": str(s)}, {"value": "0"}]} for d, ch, s in rows]})
            rows = [(LATE, "page_view", 80), (LATE, "form_start", 25), (LATE, "session_start", 40)]
            return httpx.Response(200, json={"rowCount": 3, "rows": [
                {"dimensionValues": [{"value": _g(d)}, {"value": n}], "metricValues": [{"value": str(c)}, {"value": "0"}]} for d, n, c in rows]})
        if "searchAnalytics" in url:
            if self.fail_gsc:
                return httpx.Response(403, json={"error": {"message": "User does not have sufficient permission"}})
            return httpx.Response(200, json={"rows": [
                {"keys": [LATE.isoformat(), "corporate cars melbourne"], "clicks": 3, "impressions": 100, "position": 2.5},
                {"keys": [Y.isoformat(), "chauffeur melbourne"], "clicks": 1, "impressions": 50, "position": 8.0}]})
        return httpx.Response(404)


@pytest.fixture(scope="module")
def sa_file(tmp_path_factory):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    p = tmp_path_factory.mktemp("sa") / "sa.json"
    p.write_text(json.dumps({"type": "service_account", "client_email": "bot@proj.iam.gserviceaccount.com",
                             "private_key": pem, "private_key_id": "k1", "token_uri": "https://oauth2.googleapis.com/token"}))
    return str(p)


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[t.__table__ for t in TABLES])


SITE = WebsiteRef(id=1, name="CCM", domain="corporatecarsmelbourne.com.au", base_url="https://corporatecarsmelbourne.com.au",
                  primary_service="Corporate", location="Melbourne", time_zone="Australia/Melbourne", ads_account_id=7,
                  ga4_property_id="550393874", gsc_site_url="https://corporatecarsmelbourne.com.au/")


@pytest.fixture
def google():
    return FakeGoogle()


@pytest.fixture(autouse=True)
def fakes(monkeypatch, sa_file, google):
    monkeypatch.setattr(service, "list_websites", lambda db: [SITE])
    monkeypatch.setattr(router, "list_websites", lambda db: [SITE])
    monkeypatch.setattr(service, "ads_summary", lambda db, a, d1, d2: {"totals": {"clicks": 200, "conversions": 4.0}})
    monkeypatch.setattr(service.P06Settings, "model_config", {**service.P06Settings.model_config, "env_file": None})
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", sa_file)
    real = service.execute_sync
    monkeypatch.setattr(service, "execute_sync", lambda run_id: real(
        run_id, http_factory=lambda: httpx.Client(transport=httpx.MockTransport(google.handler))))
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


# ---- adapter -------------------------------------------------------------------------------

def test_service_account_jwt_and_pagination(sa_file, google):
    calls = {"n": 0}

    def handler(req):
        if "oauth2" in str(req.url):
            return google.handler(req)
        calls["n"] += 1
        body = json.loads(req.content)
        if "analyticsdata" in str(req.url):
            off = body["offset"]
            return httpx.Response(200, json={"rowCount": 3, "rows": [{"dimensionValues": [{"value": f"e{off}"}],
                                                                      "metricValues": [{"value": "1"}]}] * (2 if off == 0 else 1)})
        n = 2 if body["startRow"] == 0 else 1
        return httpx.Response(200, json={"rows": [{"keys": ["q"], "clicks": 1, "impressions": 2, "position": 3}] * n})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        sa = ServiceAccount(sa_file, http)
        rows = GA4Client(sa).report("1", start="a", end="b", dimensions=["eventName"], metrics=["eventCount"])
        assert len(rows) == 3 and rows[0] == {"eventName": "e0", "eventCount": "1"}
        assert google.jwt_claims["iss"] == "bot@proj.iam.gserviceaccount.com" and "analytics.readonly" in google.jwt_claims["scope"]
        assert len(SearchConsoleClient(sa).query("https://x/", start="a", end="b", dimensions=["query"], row_limit=2)) == 3


def test_missing_service_account_file():
    from app.modules.p06_analytics.adapters.google import GoogleDataError

    with pytest.raises(GoogleDataError):
        ServiceAccount("/nope/sa.json", httpx.Client())


# ---- sync + overview + health -----------------------------------------------------------------

def _sync(client, days=30):
    assert client.post("/api/v1/conversions/websites/1/sync", json={"days": days}).status_code == 202
    return client.get("/api/v1/conversions/websites/1/runs").json()[0]


def test_sync_and_overview(client):
    run = _sync(client)
    assert run["status"] == "success" and run["counts"] == {"ga4_traffic": 20, "ga4_events": 3, "search_console": 2}
    ov = client.get("/api/v1/conversions/websites/1/overview?days=30").json()
    assert ov["totals"]["sessions"] == 80 and ov["channels"][0]["channel"] == "Paid Search"
    assert ov["ga4_first_day"] == LATE.isoformat()
    assert ov["top_queries"][0]["query"] == "corporate cars melbourne" and ov["organic_totals"]["clicks"] == 4
    ev = {e["event_name"]: e for e in ov["events"]}
    assert ev["form_start"]["suggested_role"] == "micro" and ev["page_view"]["suggested_role"] == "ignore"
    codes = [h["code"] for h in ov["health"]]
    assert codes[:2] == ["no_key_events", "form_submit_missing"]  # critical first
    assert {"ga4_started_late", "paid_sessions_low", "ads_vs_ga4_conversions", "no_mapping", "no_bookings"} <= set(codes)


def test_resync_replaces_rows(client):
    _sync(client)
    _sync(client)
    assert client.get("/api/v1/conversions/websites/1/overview?days=30").json()["totals"]["sessions"] == 80


def test_partial_when_search_console_denied(client, google):
    google.fail_gsc = True
    run = _sync(client)
    assert run["status"] == "partial" and "sufficient permission" in run["errors"]["search_console"]


def test_mapping_marks_event_and_clears_warning(client):
    _sync(client)
    r = client.put("/api/v1/conversions/websites/1/mappings", json={"event_name": "form_start", "role": "lead"})
    assert r.json() == {"event_name": "form_start", "role": "lead"}
    ov = client.get("/api/v1/conversions/websites/1/overview?days=30").json()
    assert next(e for e in ov["events"] if e["event_name"] == "form_start")["role"] == "lead"
    assert "no_mapping" not in [h["code"] for h in ov["health"]]
    assert client.put("/api/v1/conversions/websites/1/mappings", json={"event_name": "x", "role": "sale"}).status_code == 422


@pytest.mark.parametrize("name,role", [("generate_lead", "lead"), ("form_submit", "lead"), ("click_to_call", "lead"),
                                       ("purchase", "booking"), ("form_start", "micro"), ("first_visit", "ignore")])
def test_suggest_role(name, role):
    assert service.suggest_role(name) == role


# ---- bookings ----------------------------------------------------------------------------------

CSV = """Booking Ref,Date Booked,Total,Pickup Date,Status,Service,Website,Customer Name,Email,Phone,gclid,utm_source,utm_medium
B-1,01/09/2026,"$1,200.50",05/09/2026,Confirmed,Airport,https://www.corporatecarsmelbourne.com.au/,Jane Doe,j@x.com,0400000000,Cj0abc,,
B-2,2026-09-02,150,,cancelled,Airport,corporatecarsmelbourne.com.au,Bob,b@x.com,0411111111,,,
B-3,3/9/26,300,,confirmed,Wedding,,Ann,a@x.com,,,google,cpc
B-4,,99,,,,,,,,,,
"""


def test_import_bookings_maps_columns_and_drops_personal_data(client):
    r = client.post("/api/v1/conversions/bookings/import", json={"csv": CSV}).json()
    assert r["created"] == 3 and r["skipped"] == 1 and "line 5" in r["errors"][0]
    assert {"customer_name", "email", "phone"} <= set(r["ignored_columns"])
    with session_scope() as db:
        b1 = db.query(Booking).filter_by(external_id="B-1").one()
        assert (b1.amount, b1.booked_on, b1.service_date, b1.website_id) == (1200.5, date(2026, 9, 1), date(2026, 9, 5), 1)
        assert not any(hasattr(b1, f) for f in ("email", "phone", "customer_name"))
    s = client.get("/api/v1/conversions/bookings/summary?days=730").json()
    assert s["count"] == 2 and s["revenue"] == 1500.5  # cancelled B-2 excluded
    assert s["google_ads"] == {"count": 2, "revenue": 1500.5}  # gclid + utm google/cpc
    again = client.post("/api/v1/conversions/bookings/import", json={"csv": CSV}).json()
    assert again["created"] == 0 and again["updated"] == 3


def test_import_requires_columns(client):
    r = client.post("/api/v1/conversions/bookings/import", json={"csv": "name,email\nx,y\n"})
    assert r.status_code == 422 and "booking_id" in r.json()["error"]["message"]


def test_permissions(client, app):
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert client.post("/api/v1/conversions/websites/1/sync", json={}).status_code == 403
    assert client.post("/api/v1/conversions/bookings/import", json={"csv": CSV}).status_code == 403
    assert client.get("/api/v1/conversions/websites").status_code == 200


def test_site_without_ga4_or_gsc(client, monkeypatch):
    bare = WebsiteRef(**{**SITE.__dict__, "ga4_property_id": None, "gsc_site_url": None})
    monkeypatch.setattr(service, "list_websites", lambda db: [bare])
    r = client.post("/api/v1/conversions/websites/1/sync", json={})
    assert r.status_code == 422 and "GA4" in r.json()["error"]["message"]
