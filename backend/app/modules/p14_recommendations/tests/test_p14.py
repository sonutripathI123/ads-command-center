"""P14 tests. P05/P07/P21/P02 replaced through their public interfaces; Claude is never called for real."""
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p14_recommendations import ai, router, service
from app.modules.p14_recommendations.models import AIEvidence, AIRun, Recommendation
from app.modules.p21_business_rules.interface import Rules
from app.shared.db import Base, get_engine, session_scope
from app.shared.feature_flags import FeatureFlagOverride

pytestmark = pytest.mark.module("P14")
TABLES = [AIEvidence, AIRun, Recommendation]
ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="", currency_code="AUD")


def issue(code, sev="warning", cat="keywords", conf=0.7, risk="low", entity=""):
    return {"code": code, "category": cat, "severity": sev, "title": f"T {code}", "observation": "obs",
            "evidence": [["Cost", "AUD 10"]], "reasoning": "why", "proposed_action": "do x", "expected_impact": "better",
            "confidence": conf, "risk": risk, "entity_type": "account", "entity_id": entity, "link": "/audit"}


AUDIT = {"score": 20, "created_at": datetime.now(UTC), "days": 90, "counts": {},
         "issues": [issue("no_key_events", "critical", "tracking", 0.9), issue("low_quality_score"),
                    issue("smart_bidding", "critical", "bidding", 0.75, "medium"), issue("brand", "info", "organic", 0.6)]}


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[t.__table__ for t in reversed(TABLES)])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    state = {"audit": dict(AUDIT)}
    monkeypatch.setattr(service, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(router, "list_accounts", lambda db: [ACC])
    monkeypatch.setattr(service, "latest_audit", lambda db, a: state["audit"])
    monkeypatch.setattr(service, "summary", lambda db, a, d1, d2: {"totals": {"clicks": 600, "conversions": 5, "cost": 1500}})
    monkeypatch.setattr(service, "get_rules", lambda db, a: Rules())
    monkeypatch.setattr(ai.P14Settings, "model_config", {**ai.P14Settings.model_config, "env_file": None})
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    yield state
    with session_scope() as db:
        for t in TABLES:
            db.execute(delete(t))
        db.execute(delete(FeatureFlagOverride))


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


B = "/api/v1/recommendations"


def test_refresh_ingests_audit_in_priority_order(client):
    r = client.post(f"{B}/accounts/7/refresh").json()
    assert r["new"] == 4 and r["superseded"] == 0
    recs = client.get(f"{B}/accounts/7").json()
    assert [x["title"] for x in recs] == ["T no_key_events", "T smart_bidding", "T low_quality_score", "T brand"]
    assert recs[0]["priority"] == 390 and recs[1]["priority"] == 355  # 300+75-20
    assert recs[0]["requires_approval"] is False  # tracking is fixed outside Google Ads
    assert recs[1]["requires_approval"] is True   # bidding change inside Google Ads
    assert {"observation", "evidence", "reasoning", "proposed_action", "expected_impact", "confidence", "risk", "status"} <= set(recs[0])


def test_refresh_is_idempotent_and_supersedes(client, fakes):
    client.post(f"{B}/accounts/7/refresh")
    fakes["audit"] = {**AUDIT, "issues": AUDIT["issues"][:2]}
    r = client.post(f"{B}/accounts/7/refresh").json()
    assert r["new"] == 0 and r["superseded"] == 2
    assert len(client.get(f"{B}/accounts/7").json()) == 2
    assert len(client.get(f"{B}/accounts/7?status=superseded").json()) == 2


def test_refresh_needs_an_audit(client, fakes):
    fakes["audit"] = None
    assert client.post(f"{B}/accounts/7/refresh").status_code == 422


def test_status_workflow(client):
    client.post(f"{B}/accounts/7/refresh")
    rid = client.get(f"{B}/accounts/7").json()[0]["id"]
    a = client.post(f"{B}/{rid}/status", json={"status": "accepted", "note": "doing it"}).json()
    assert a["status"] == "accepted" and a["approved_at"] and a["decided_by"] == "me@example.com"
    d = client.post(f"{B}/{rid}/status", json={"status": "done"}).json()
    assert d["status"] == "done" and d["executed_at"]
    assert client.post(f"{B}/{rid}/status", json={"status": "rejected"}).status_code == 422  # done → rejected not allowed
    client.post(f"{B}/accounts/7/refresh")  # decision survives refresh
    assert client.get(f"{B}/accounts/7?status=done").json()[0]["id"] == rid


def test_template_plan_when_ai_off(client):
    client.post(f"{B}/accounts/7/refresh")
    st = client.get(f"{B}/ai-status").json()
    assert st == {"flag_enabled": False, "api_key_configured": False, "live": False, "model": "claude-opus-5"}
    run = client.post(f"{B}/accounts/7/plan").json()
    assert run["mode"] == "template" and run["status"] == "success" and run["model"] is None
    plan = run["plan"]
    assert plan["top_actions"][0]["title"] == "T no_key_events" and plan["top_actions"][0]["owner"] == "website developer"
    assert [w["week"] for w in plan["thirty_day_plan"]] == [1, 2, 3, 4]
    assert client.get(f"{B}/accounts/7/plan").json()["run"]["id"] == run["id"]


def test_live_plan_uses_claude_and_drops_unknown_ids(client, monkeypatch):
    client.post(f"{B}/accounts/7/refresh")
    with session_scope() as db:
        db.merge(FeatureFlagOverride(key="ai.live_calls.enabled", enabled=True, reason="test"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    seen = {}

    def fake_claude(prompt, settings):
        seen["prompt"], seen["key"] = prompt, settings.anthropic_api_key
        with session_scope() as s:
            ids = [r.id for r in service.list_recs(s, 7)][:1]
        plan = ai.ActionPlan(summary="Fix tracking first.", top_actions=[ai.Action(
            title="Fix tracking", why="no data", steps=["add generate_lead"], owner="website developer", effort="low",
            recommendation_ids=ids + [99999])], thirty_day_plan=[ai.Week(week=1, focus="Measure", tasks=["x"]), ai.Week(week=1, focus="", tasks=[])],
            measure=["leads"], caveats=[])
        return plan, 1200, 800, "claude-opus-5"

    monkeypatch.setattr(ai, "call_claude", fake_claude)
    run = client.post(f"{B}/accounts/7/plan").json()
    assert run["mode"] == "live" and run["model"] == "claude-opus-5" and run["output_tokens"] == 800
    assert 99999 not in run["plan"]["top_actions"][0]["recommendation_ids"]
    assert [w["focus"] for w in run["plan"]["thirty_day_plan"]] == ["Measure"]  # empty week dropped
    assert seen["key"] == "test-key" and "T no_key_events" in seen["prompt"] and "1949408641" in seen["prompt"]
    with session_scope() as db:
        assert db.query(AIEvidence).filter_by(run_id=run["id"]).count() == 4


def test_live_plan_error_is_recorded(client, monkeypatch):
    client.post(f"{B}/accounts/7/refresh")
    with session_scope() as db:
        db.merge(FeatureFlagOverride(key="ai.live_calls.enabled", enabled=True, reason="test"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "bad")

    def boom(prompt, settings):
        raise ai.AIError("Claude API key is invalid (ANTHROPIC_API_KEY)")

    monkeypatch.setattr(ai, "call_claude", boom)
    run = client.post(f"{B}/accounts/7/plan").json()
    assert run["status"] == "failed" and "invalid" in run["error"] and run["plan"] is None


def test_plan_schema_is_strict():
    def walk(s):
        if s.get("type") == "object":
            assert s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])
            for v in s["properties"].values():
                walk(v)
        if s.get("type") == "array":
            walk(s["items"])

    walk(ai.PLAN_SCHEMA)
    assert "never promise" in ai.SYSTEM


def test_permissions(client, app):
    client.post(f"{B}/accounts/7/refresh")
    rid = client.get(f"{B}/accounts/7").json()[0]["id"]
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ, Permission.RECOMMEND})
    assert client.post(f"{B}/{rid}/status", json={"status": "accepted"}).status_code == 403  # approve needed
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert client.post(f"{B}/accounts/7/refresh").status_code == 403
    assert client.post(f"{B}/accounts/7/plan").status_code == 403
    assert client.get(f"{B}/accounts/7").status_code == 200
    assert client.get(f"{B}/accounts/99").status_code == 404
