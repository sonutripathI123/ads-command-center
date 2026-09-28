"""P09 tests. P05/P21/P02 replaced via their public interfaces; Claude never called for real."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p09_ad_creative import router, service, writer
from app.modules.p09_ad_creative.checks import check_ad, check_text, strength
from app.modules.p09_ad_creative.models import AdDraft, ClaimCheck
from app.modules.p21_business_rules.interface import Rules
from app.shared.db import Base, get_engine, session_scope
from app.shared.feature_flags import FeatureFlagOverride

pytestmark = pytest.mark.module("P09")
KW = dict(approved_claims=[], competitors=["blacklane"])


def codes(fs):
    return {f.code for f in fs}


@pytest.mark.parametrize("field,text,code", [
    ("headline", "Melbourne Airport Chauffeur Transfers 24/7", "too_long"),
    ("headline", "Book Now!", "exclamation_in_headline"),
    ("headline", "Call 0412 345 678", "phone_in_text"),
    ("headline", "BEST Chauffeurs", "all_caps"),
    ("headline", "Better than Blacklane", "competitor_name"),
    ("headline", "#1 Chauffeur Melbourne", "unverified_claim"),
    ("description", "Cheapest airport transfers.. book", "repeated_punctuation"),
    ("path", "airport/cars", "path_chars"),
    ("headline", "Luxury Cars 🚗", "emoji"),
])
def test_text_rules(field, text, code):
    assert code in codes(check_text(field, 0, text, **KW))


def test_approved_claim_is_not_flagged():
    assert "unverified_claim" not in codes(check_text("headline", 0, "Fixed price transfers", approved_claims=["fixed price"], competitors=[]))
    assert "unverified_claim" in codes(check_text("headline", 0, "Best Chauffeur Service", approved_claims=["fixed price"], competitors=[]))


def test_ad_level_rules_and_strength():
    f = check_ad(["Airport Chauffeur", "Airport Chauffeur"], ["One."], [], keywords=["corporate cars"], locations=["melbourne"], **KW)
    assert {"too_few_headlines", "too_few_descriptions", "duplicate_headlines", "no_keyword_in_headlines",
            "no_call_to_action", "no_location"} <= codes(f)
    good_h = ["Corporate Cars Melbourne", "Book a Chauffeur Today", "Airport Transfers", "Get an Instant Quote",
              "Professional Drivers", "Late-Model Sedans", "Meet & Greet Service", "Corporate Travel Melbourne"]
    good_d = ["Corporate cars across Melbourne with professional chauffeurs. Book online today.",
              "Reliable airport and business transfers. Get your quote in minutes."]
    g = check_ad(good_h, good_d, ["Corporate", "Melbourne"], keywords=["corporate cars"], locations=["melbourne"], **KW)
    assert not [x for x in g if x.severity == "error"]
    assert strength(good_h, good_d, g) > strength(["A", "B", "C"], good_d, check_ad(["A", "B", "C"], good_d, [], keywords=[], locations=[], **KW))


def test_template_copy_passes_all_hard_rules():
    c = writer.template_copy("Airport Transfers", ["melbourne airport transfer", "airport chauffeur melbourne"],
                             ["melbourne"], ["fixed price", "flight tracking"], "Corporate Cars Melbourne")
    f = check_ad(c.headlines, c.descriptions, [c.path1, c.path2], keywords=["melbourne airport transfer"],
                 locations=["melbourne"], approved_claims=["fixed price", "flight tracking"], competitors=[])
    assert len(c.headlines) == 15 and len(c.descriptions) == 4
    assert not [x for x in f if x.severity == "error"], [x.message for x in f]


def test_schema_is_strict():
    assert writer.SCHEMA["additionalProperties"] is False and set(writer.SCHEMA["required"]) == set(writer.SCHEMA["properties"])


# ---- API ------------------------------------------------------------------------------------------

ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="")
ADS = [{"key": "10~1", "ad_id": "1", "type": "RESPONSIVE_SEARCH_AD", "status": "ENABLED", "campaign_name": "Search",
        "ad_group_name": "Airport", "final_urls": ["https://corporatecarsmelbourne.com.au/airport"],
        "headlines": ["Airport Chauffeur", "Book Now!"], "descriptions": ["Great service."],
        "cost": 50.0, "clicks": 20, "impressions": 200, "ctr": 0.1, "conversions": 0.0}]
GROUPS = [{"google_id": "10", "name": "Airport", "campaign_name": "Search", "status": "ENABLED"}]
KWS = [{"ad_group_google_id": "10", "text": "melbourne airport transfer", "status": "ENABLED", "impressions": 100, "clicks": 10}]


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[AdDraft.__table__, ClaimCheck.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(service, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(router, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(service, "ads", lambda db, a, d1, d2: ADS)
    monkeypatch.setattr(service, "ad_groups", lambda db, a, d1, d2: GROUPS)
    monkeypatch.setattr(service, "keywords", lambda db, a, d1, d2: KWS)
    monkeypatch.setattr(service, "get_rules", lambda db, a=None: Rules(brand_terms=["corporate cars melbourne"]))
    monkeypatch.setattr(writer.P09Settings, "model_config", {**writer.P09Settings.model_config, "env_file": None})
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    yield
    with session_scope() as db:
        db.execute(delete(ClaimCheck))
        db.execute(delete(AdDraft))
        db.execute(delete(FeatureFlagOverride))


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


B = "/api/v1/creatives"


def test_existing_ad_analysis(client):
    rows = client.get(f"{B}/accounts/7/analysis").json()
    r = rows[0]
    fc = {f["code"] for f in r["findings"]}
    assert {"exclamation_in_headline", "too_few_headlines", "too_few_descriptions"} <= fc and r["strength"] < 50


def test_ad_group_options_have_keywords_and_url(client):
    g = client.get(f"{B}/accounts/7/ad-groups").json()[0]
    assert g["keywords"] == ["melbourne airport transfer"] and g["final_url"].endswith("/airport")


def _new(client, **kw):
    body = {"ad_group_name": "Airport", "campaign_name": "Search", "ad_group_google_id": "10",
            "final_url": "https://corporatecarsmelbourne.com.au/airport", "keywords": ["melbourne airport transfer"],
            "usps": ["Fixed price", "Flight tracking"]} | kw
    return client.post(f"{B}/accounts/7/drafts", json=body)


def test_template_draft_when_ai_off(client):
    d = _new(client).json()
    assert d["mode"] == "template" and len(d["headlines"]) == 15 and d["status"] == "draft"
    assert not [c for c in d["checks"] if c["severity"] == "error"] and d["strength"] >= 80


def test_live_draft_uses_claude(client, monkeypatch):
    with session_scope() as db:
        db.merge(FeatureFlagOverride(key="ai.live_calls.enabled", enabled=True, reason="t"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    seen = {}

    def fake(brief, settings):
        seen["brief"] = brief
        return writer.AdCopy(headlines=["Melbourne Airport Transfer", "Book Now!"] + [f"Headline {i}" for i in range(13)],
                             descriptions=["A.", "B.", "C.", "D."], path1="Airport", path2="Melbourne", notes="used fixed price"), 900, 600, "claude-opus-5"

    monkeypatch.setattr(writer, "write_with_claude", fake)
    d = _new(client).json()
    assert d["mode"] == "live" and d["model"] == "claude-opus-5" and d["output_tokens"] == 600
    assert "Fixed price" in seen["brief"] and "Airport Chauffeur" in seen["brief"]  # USPs + existing headlines
    assert any(c["code"] == "exclamation_in_headline" and c["index"] == 1 for c in d["checks"])


def test_ai_failure_is_a_clear_error(client, monkeypatch):
    with session_scope() as db:
        db.merge(FeatureFlagOverride(key="ai.live_calls.enabled", enabled=True, reason="t"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    def boom(brief, settings):
        raise writer.WriterError("Claude API rate limit reached — try again in a minute")

    monkeypatch.setattr(writer, "write_with_claude", boom)
    r = _new(client)
    assert r.status_code == 502 and "rate limit" in r.json()["error"]["message"]


def test_edit_recheck_approve_and_export(client):
    d = _new(client).json()
    bad = d["headlines"][:14] + ["Book Now!"]
    r = client.patch(f"{B}/drafts/{d['id']}", json={"headlines": bad, "status": "approved"})
    assert r.status_code == 422 and "Fix the errors" in r.json()["error"]["message"]
    ok = client.patch(f"{B}/drafts/{d['id']}", json={"headlines": d["headlines"], "status": "approved"}).json()
    assert ok["status"] == "approved" and ok["reviewed_by"] == "me@example.com"
    csv = client.get(f"{B}/accounts/7/drafts/export").text.splitlines()
    assert csv[0].startswith("Campaign,Ad group,Headline 1") and "Paused" in csv[1] and "Airport" in csv[1]


def test_permissions(client, app):
    d = _new(client).json()
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ, Permission.RECOMMEND})
    assert client.patch(f"{B}/drafts/{d['id']}", json={"status": "approved"}).status_code == 403
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert _new(client).status_code == 403
    assert client.get(f"{B}/accounts/7/drafts").status_code == 200
