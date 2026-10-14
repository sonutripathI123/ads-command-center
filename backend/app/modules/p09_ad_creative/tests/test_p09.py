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
TERMS = [{"search_term": "melbourne airport chauffeur", "conversions": 2.0, "cost": 30.0, "clicks": 12}]
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
    monkeypatch.setattr(service, "search_terms", lambda db, a, d1, d2, **kw: TERMS)
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


# ---- Smart ad copy --------------------------------------------------------------------------------

from app.modules.p09_ad_creative import context  # noqa: E402


def _ad(h, conv, cost, clicks, ctr, impr=500, ag="G"):
    return {"type": "RESPONSIVE_SEARCH_AD", "headlines": h, "descriptions": ["d1", "d2"], "conversions": conv, "cost": cost,
            "clicks": clicks, "ctr": ctr, "impressions": impr, "ad_group_name": ag}


POOL = [_ad(["A1"], 4, 100, 50, 0.05), _ad(["B1"], 1, 20, 30, 0.04), _ad(["C1"], 0, 80, 40, 0.01),
        _ad(["D1"], 0, 5, 3, 0.02), _ad(["E1"], 2, 400, 60, 0.09)]


def test_split_ads_by_goal():
    w, l = context.split_ads(POOL, "conversions")
    assert [a["headlines"][0] for a in w] == ["A1", "E1", "B1"] and [a["headlines"][0] for a in l] == ["C1"]  # D1: too little spend
    w, _ = context.split_ads(POOL, "cpa")
    assert [a["headlines"][0] for a in w] == ["B1", "A1", "E1"]                                               # cheapest conversion first
    w, l = context.split_ads(POOL, "clicks")
    assert w[0]["headlines"][0] == "E1" and "C1" in [a["headlines"][0] for a in l]                             # best / worst CTR


def test_avoid_lines_dedupes_and_caps():
    hs, ds = context.avoid_lines([{"headlines": ["Book Now", "book now", "Other"], "descriptions": ["Desc"]},
                                  {"headlines": [f"H{i}" for i in range(100)], "descriptions": []}])
    assert hs[:2] == ["Book Now", "Other"] and len(hs) == context.MAX_AVOID_HEADLINES and ds == ["Desc"]


def test_build_flags_small_samples_and_forbids_numbers():
    text, summary = context.build("conversions", [POOL[0]], [POOL[2]], [{"search_term": "x", "conversions": 1, "cost": 5}], ["Old H"], [])
    assert "hints, not proof" in text and "Never quote any number" in text and "do NOT reuse" in text and "Old H" in text
    assert summary == {"goal": "conversions", "winners": 1, "losers": 1, "terms": 1, "avoided": 1}


def test_repeat_count_and_note():
    assert context.repeat_count(["Book Now", "New"], ["Same"], ["book now"], ["same"]) == 2
    n = context.note({"goal": "clicks", "winners": 0, "losers": 0, "terms": 0, "avoided": 0}, "template", 0)
    assert "Template mode cannot learn" in n
    assert context.note(None, "live", 0) == ""


def test_smart_copy_sends_history_to_claude_and_notes_repeats(client, monkeypatch):
    with session_scope() as db:
        db.merge(FeatureFlagOverride(key="ai.live_calls.enabled", enabled=True, reason="t"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(service, "ads", lambda db, a, d1, d2: [_ad(["Airport Chauffeur"], 3, 90, 40, 0.06, ag="Airport"),
                                                               _ad(["Wasted Line"], 0, 70, 30, 0.01, ag="Airport")])
    seen = {}

    def fake(brief, settings):
        seen["brief"] = brief
        return writer.AdCopy(headlines=["Airport Chauffeur"] + [f"Fresh {i}" for i in range(14)], descriptions=["A.", "B.", "C.", "D."],
                             path1="Airport", path2="Melbourne", notes="used fixed price"), 900, 600, "claude-opus-5"

    monkeypatch.setattr(writer, "write_with_claude", fake)
    d = _new(client, goal="cpa").json()
    b = seen["brief"]
    assert "lower the cost per conversion" in b and "melbourne airport chauffeur" in b and "RECENTLY WRITTEN OR RUN COPY" in b
    assert "Wasted Line" in b and "Airport Chauffeur" in b
    assert "Smart ad copy" in d["notes"] and "1 line(s) still repeat" in d["notes"]


def test_second_draft_avoids_the_first(client, monkeypatch):
    with session_scope() as db:
        db.merge(FeatureFlagOverride(key="ai.live_calls.enabled", enabled=True, reason="t"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    briefs = []

    def fake(brief, settings):
        briefs.append(brief)
        return writer.AdCopy(headlines=[f"Take {len(briefs)} H{i}" for i in range(15)], descriptions=["A.", "B.", "C.", "D."],
                             path1="Airport", path2="Melbourne", notes="n"), 1, 1, "claude-opus-5"

    monkeypatch.setattr(writer, "write_with_claude", fake)
    _new(client)
    _new(client)
    assert "Take 1 H0" not in briefs[0] and "Take 1 H0" in briefs[1]   # the first draft is on the second one's avoid list


def test_learn_off_adds_nothing_and_template_says_so(client):
    d = _new(client, learn=False).json()
    assert "Smart ad copy" not in d["notes"]
    t = _new(client).json()
    assert "Template mode cannot learn" in t["notes"]


def test_history_source_failure_does_not_block_drafting(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(service, "search_terms", boom)
    d = _new(client)
    assert d.status_code == 201 and "No history" in d.json()["notes"] or "Template mode cannot learn" in d.json()["notes"]


def test_keywords_lose_match_type_decoration(client, monkeypatch):
    assert service.clean_keywords(["[executive chauffeur melbourne]", '"vip chauffeur hire"', "+limo +hire", "  ", "VIP chauffeur hire"]) ==         ["executive chauffeur melbourne", "vip chauffeur hire", "limo hire"]
    d = _new(client, keywords=["[melbourne airport transfer]", '"melbourne airport transfer"']).json()
    assert d["keywords"] == ["melbourne airport transfer"]


def test_bad_goal_is_rejected(client):
    assert _new(client, goal="revenue").status_code == 422


# ---- Campaign review: strength + suggestions -----------------------------------------------------------

from app.modules.p09_ad_creative import review  # noqa: E402


def _row(**kw):
    base = {"headlines": ["h"] * 15, "descriptions": ["d"] * 4, "strength": 90, "findings": [], "impressions": 1000, "clicks": 50,
            "cost": 100.0, "conversions": 2.0, "ctr": 0.05}
    return base | kw


BENCH = {"ctr": 0.05, "cpa": 50.0}


def test_benchmark_is_account_wide():
    b = review.benchmark([_row(impressions=1000, clicks=50, cost=100, conversions=2), _row(impressions=1000, clicks=100, cost=300, conversions=2)])
    assert b == {"ctr": 0.075, "cpa": 100.0}
    assert review.benchmark([_row(impressions=0, clicks=0, cost=0, conversions=0)]) == {"ctr": None, "cpa": None}


def test_suggestions_cover_structure_and_performance():
    s = " | ".join(review.suggest(_row(headlines=["a"] * 9, descriptions=["d"] * 2, strength=40,
                                       findings=[{"severity": "error", "message": "Headline too long"}]), BENCH))
    assert "Fix 1 error" in s and "Add 6 more headline" in s and "Add 2 more description" in s and "strength is low" in s
    assert "no conversion" in " ".join(review.suggest(_row(conversions=0.0, cost=80.0, clicks=40), BENCH))
    assert "well below" in " ".join(review.suggest(_row(ctr=0.01), BENCH))
    assert "above the account" in " ".join(review.suggest(_row(cost=500.0, conversions=2.0), BENCH))
    assert "Converts cheaper" in " ".join(review.suggest(_row(cost=40.0, conversions=2.0), BENCH))


def test_suggestions_are_honest_without_data():
    s = review.suggest(_row(impressions=0, clicks=0, cost=0.0, conversions=0.0, ctr=None), BENCH)
    assert any("cannot be judged" in x for x in s)
    assert not any("no conversion" in x for x in s)
    assert review.suggest(_row(conversions=5.0, cost=250.0), BENCH) == ["Nothing urgent. Keep it running and re-check when there is more data."]
    assert any("Only a few conversions" in x for x in review.suggest(_row(), BENCH))


def test_analysis_filters_by_campaign_and_adds_suggestions(client, monkeypatch):
    other = dict(ADS[0], key="10~2", ad_id="2", campaign_name="Other", headlines=["x"] * 15, descriptions=["y"] * 4)
    monkeypatch.setattr(service, "ads", lambda db, a, d1, d2: ADS + [other])
    all_rows = client.get(f"{B}/accounts/7/analysis").json()
    assert {r["campaign_name"] for r in all_rows} == {"Search", "Other"}
    rows = client.get(f"{B}/accounts/7/analysis", params={"campaign": "Search"}).json()
    assert [r["campaign_name"] for r in rows] == ["Search"] and rows[0]["suggestions"] and rows[0]["benchmark"]["ctr"] is not None
    assert client.get(f"{B}/accounts/7/analysis", params={"campaign": "Nope"}).json() == []
