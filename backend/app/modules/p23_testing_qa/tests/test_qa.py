"""P23 tests. Two jobs: test the harness itself (fakes, fixtures) and run the product-wide QA audits
(access rules on every route, locked execution) as a permanent regression suite."""
import json

import pytest
from fastapi.testclient import TestClient

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p23_testing_qa.interface import (
    PUBLIC_ROUTES,
    FakeAdsAPI,
    FakeAIError,
    FakeClaude,
    MutationAttempted,
    audit_anonymous,
    audit_read_only_writes,
    list_fixtures,
    list_routes,
    load_fixture,
)
from app.shared.db import session_scope
from app.shared.feature_flags import FeatureFlagOverride, is_enabled

pytestmark = pytest.mark.module("P23")


@pytest.fixture(scope="module")
def app():
    from app.main import create_app

    return create_app()


@pytest.fixture
def client(app):
    app.dependency_overrides.clear()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ---- harness: fixtures ----------------------------------------------------------------------------

def test_recorded_ad_copy_fixture_obeys_google_limits():
    c = load_fixture("ad_copy_ok")
    assert len(c["headlines"]) == 15 and len(set(h.lower() for h in c["headlines"])) == 15
    assert all(len(h) <= 30 for h in c["headlines"]) and len(c["descriptions"]) == 4
    assert all(len(d) <= 90 for d in c["descriptions"]) and len(c["path1"]) <= 15 and len(c["path2"]) <= 15
    assert not any("!" in h for h in c["headlines"])


def test_every_fixture_is_valid_json_and_listed():
    assert {"ad_copy_ok", "ai_refusal"} <= set(list_fixtures())
    for n in list_fixtures():
        assert isinstance(load_fixture(n), dict)


# ---- harness: FakeClaude --------------------------------------------------------------------------

def test_fake_claude_replays_in_order_and_records_prompts():
    fc = FakeClaude(["ad_copy_ok", {"headlines": ["x"]}])
    assert fc.ask("first")["path1"] == "Melbourne"
    assert fc.ask("second") == {"headlines": ["x"]} and fc.ask("third") == {"headlines": ["x"]}   # last answer repeats
    assert fc.prompts == ["first", "second", "third"] and fc.calls == 3


@pytest.mark.parametrize("kind", ["rate_limit", "refusal", "cut_off", "network"])
def test_fake_claude_failure_modes(kind):
    fc = FakeClaude("ad_copy_ok", fail=kind)
    with pytest.raises(FakeAIError) as e:
        fc.ask("p")
    assert e.value.kind == kind and fc.calls == 1


# ---- harness: FakeAdsAPI --------------------------------------------------------------------------

def test_fake_ads_api_reads_but_refuses_every_mutation():
    api = FakeAdsAPI({"campaign": [{"id": 1}]})
    assert api.read("campaign") == [{"id": 1}] and api.read("keyword") == [] and api.calls == ["read:campaign", "read:keyword"]
    for name in ("mutate", "mutate_operations", "create_campaign", "update_budget", "remove_keyword", "set_status"):
        with pytest.raises(MutationAttempted):
            getattr(api, name)()
    with pytest.raises(AttributeError):
        api.something_else


# ---- audits: access rules on the real app -----------------------------------------------------------

def test_route_inventory_is_complete(app):
    routes = list_routes(app)
    assert len(routes) >= 100 and PUBLIC_ROUTES <= set(routes)
    assert {m for m, _ in routes} == {"GET", "POST", "PATCH", "PUT", "DELETE"}


def test_every_protected_route_refuses_anonymous_callers(client, app):
    findings = audit_anonymous(client, app)
    assert not findings, "\n".join(map(str, findings))


def test_a_read_only_user_cannot_write_anywhere(client, app):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=0, email="viewer@example.com", name="v", role="viewer", permissions=frozenset({Permission.READ}))
    findings = audit_read_only_writes(client, app)
    assert not findings, "\n".join(map(str, findings))


def test_recommend_only_user_cannot_approve_or_execute(client, app):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=0, email="analyst@example.com", name="a", role="analyst",
        permissions=frozenset({Permission.READ, Permission.RECOMMEND}))
    for decision in ("approve", "reject"):   # the permission is checked once the body names the decision
        assert client.post("/api/v1/approvals/1/decision", json={"decision": decision}).status_code == 403, decision
    for path in ("/api/v1/execution/approvals/1/execute", "/api/v1/execution/approvals/1/validate",
                 "/api/v1/execution/executions/1/rollback"):
        assert client.post(path, json={}).status_code == 403, path


def test_approver_without_execute_cannot_run_live_changes(client, app):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=0, email="approver@example.com", name="p", role="approver",
        permissions=frozenset({Permission.READ, Permission.RECOMMEND, Permission.APPROVE}))
    for path in ("/api/v1/execution/approvals/1/execute", "/api/v1/execution/executions/1/rollback"):
        assert client.post(path, json={}).status_code == 403, path


# ---- regression: live Google Ads execution stays locked ---------------------------------------------

GUARDED = ("ads.execution.enabled", "ads.execution.automation.enabled")


def test_guarded_flags_are_off_by_default(client):
    body = client.get("/api/v1/foundation/flags").json()
    flags = {f["key"]: f["enabled"] for f in (body if isinstance(body, list) else body["flags"])}
    assert all(flags[k] is False for k in GUARDED)
    assert client.get("/api/v1/foundation/health").json()["execution_kill_switch"] is True


@pytest.fixture
def clean_flags():
    yield
    with session_scope() as db:
        for k in GUARDED:
            row = db.get(FeatureFlagOverride, k)
            if row:
                db.delete(row)


def test_kill_switch_beats_any_override(clean_flags, settings_override):
    with session_scope() as db:
        for k in GUARDED:
            db.merge(FeatureFlagOverride(key=k, enabled=True, reason="qa"))
    settings_override(ads_execution_kill_switch=True)
    with session_scope() as db:
        assert [is_enabled(k, db) for k in GUARDED] == [False, False]
    settings_override(ads_execution_kill_switch=False)
    with session_scope() as db:
        assert [is_enabled(k, db) for k in GUARDED] == [True, True]   # only an operator lifting the switch can enable them


def test_fixtures_are_plain_json_text():
    for n in list_fixtures():
        assert json.loads(json.dumps(load_fixture(n))) == load_fixture(n)
