"""P17 tests. NO real network: Google is a fake httpx MockTransport; P04/P05/P09/P16 are replaced through their interfaces."""
import json
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p04_ads_connection.interface import AccountRef, ApiCredentials
from app.modules.p17_ads_execution import google, plans, service
from app.modules.p17_ads_execution.models import Execution
from app.modules.p22_security_audit import interface as _p22  # noqa: F401 — registers the audit_logs table
from app.shared.db import Base, get_engine, session_scope
from app.shared.errors import FeatureDisabled, ValidationFailed

pytestmark = pytest.mark.module("P17")

ACC = AccountRef(id=7, customer_id="1234567890", descriptive_name="CCM", currency_code="AUD", time_zone="Australia/Melbourne",
                 login_customer_id=None)
CAMPAIGNS = [{"google_id": "11", "status": "ENABLED"}, {"google_id": "22", "status": "PAUSED"}, {"google_id": "33", "status": "REMOVED"}]
NEG = [{"text": "free car rental", "match_type": "PHRASE", "level": "campaign", "campaign_id": "11"},
       {"text": "hertz", "match_type": "EXACT", "level": "account", "campaign_id": None}]


# ---- plans (pure) -------------------------------------------------------------------------------------

def test_negatives_plan_campaign_and_account_level():
    (op,) = plans.negatives_plan("123", NEG, CAMPAIGNS)
    creates = [o["create"] for o in op.operations]
    assert op.service == "campaignCriteria" and len(creates) == 3          # 1 campaign-level + account-level × 2 live campaigns
    assert all(c["negative"] is True for c in creates)
    assert {c["campaign"] for c in creates} == {"customers/123/campaigns/11", "customers/123/campaigns/22"}
    assert creates[0]["keyword"] == {"text": "free car rental", "matchType": "PHRASE"}


def test_negatives_plan_rejects_bad_input_and_dedupes():
    with pytest.raises(plans.PlanError):
        plans.negatives_plan("123", [], CAMPAIGNS)
    with pytest.raises(plans.PlanError):
        plans.negatives_plan("123", [{"text": "x", "match_type": "WEIRD", "campaign_id": "11"}], CAMPAIGNS)
    (op,) = plans.negatives_plan("123", [NEG[0], NEG[0]], CAMPAIGNS)
    assert len(op.operations) == 1


def test_operation_cap():
    many = [{"text": f"t{i}", "match_type": "EXACT", "campaign_id": "11"} for i in range(plans.MAX_OPERATIONS + 1)]
    with pytest.raises(plans.PlanError):
        plans.negatives_plan("123", many, CAMPAIGNS)


AFTER = {"headlines": ["a", "b", "c"], "descriptions": ["d1", "d2"], "final_url": "https://x.com.au/", "paths": ["airport", ""]}
DRAFT = {"id": 5, "ad_group_google_id": "999", "ad_group_name": "Airport", "headlines": ["a", "b", "c"],
         "descriptions": ["d1", "d2"], "final_url": "https://x.com.au/"}


def test_rsa_plan_is_paused_and_shaped():
    (op,) = plans.rsa_plan("123", AFTER, DRAFT)
    c = op.operations[0]["create"]
    assert op.service == "adGroupAds" and c["status"] == "PAUSED" and c["adGroup"] == "customers/123/adGroups/999"
    assert c["ad"]["responsiveSearchAd"]["path1"] == "airport" and "path2" not in c["ad"]["responsiveSearchAd"]


def test_rsa_plan_blocks_unlinked_or_changed_drafts():
    with pytest.raises(plans.PlanError):
        plans.rsa_plan("123", AFTER, DRAFT | {"ad_group_google_id": None})
    with pytest.raises(plans.PlanError):
        plans.rsa_plan("123", AFTER, DRAFT | {"headlines": ["a", "b", "EDITED"]})


def test_plan_hash_changes_with_content():
    a, b = plans.negatives_plan("123", NEG, CAMPAIGNS), plans.negatives_plan("123", NEG[:1], CAMPAIGNS)
    assert plans.plan_hash(a) == plans.plan_hash(plans.negatives_plan("123", NEG, CAMPAIGNS)) and plans.plan_hash(a) != plans.plan_hash(b)


def test_body_carries_validate_flag_explicitly():
    (op,) = plans.negatives_plan("123", NEG[:1], CAMPAIGNS)
    assert op.body(validate_only=True)["validateOnly"] is True and op.body(validate_only=False)["validateOnly"] is False


# ---- the choke point -----------------------------------------------------------------------------------

CALLS: list[httpx.Request] = []


def _creds(responder=None):
    def handler(req: httpx.Request) -> httpx.Response:
        CALLS.append(req)
        if responder:
            return responder(req)
        body = json.loads(req.content)
        if body["validateOnly"]:
            return httpx.Response(200, json={})
        n = len(body["operations"])
        return httpx.Response(200, json={"results": [{"resourceName": f"customers/1234567890/campaignCriteria/11~{i}"} for i in range(n)]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ApiCredentials(account=ACC, http=client, base_url="https://googleads.test/v25", _headers={"Authorization": "Bearer t"})


def test_live_send_is_blocked_by_kill_switch_before_any_http(db):
    CALLS.clear()
    (op,) = plans.negatives_plan("1234567890", NEG[:1], CAMPAIGNS)
    with pytest.raises(FeatureDisabled):
        google.send(db, _creds(), op, validate_only=False)
    assert CALLS == []                                  # not a single request left the process


def test_validate_send_never_changes_anything_and_hits_the_right_url(db):
    CALLS.clear()
    (op,) = plans.negatives_plan("1234567890", NEG[:1], CAMPAIGNS)
    google.send(db, _creds(), op, validate_only=True)
    assert str(CALLS[0].url) == "https://googleads.test/v25/customers/1234567890/campaignCriteria:mutate"
    assert json.loads(CALLS[0].content)["validateOnly"] is True


def _audit(db, extra=""):
    return db.execute(text(f"SELECT COUNT(*) FROM audit_logs WHERE module_id = 'P17' {extra}")).scalar()


# ---- service flow ----------------------------------------------------------------------------------------

APPROVAL = {"id": 1, "account_id": 7, "status": "approved", "change_type": "add_negative_keywords", "title": "Add negatives",
            "payload": {"negatives": NEG}, "after": {}, "impact": "standard", "risk": "low", "decided_by": "boss"}
STATE = {"approval": dict(APPROVAL), "marked": [], "creds": None}


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[Execution.__table__, Base.metadata.tables["audit_logs"]])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    STATE.update(approval=dict(APPROVAL), marked=[], creds=_creds)
    CALLS.clear()
    monkeypatch.setattr(service, "active_accounts", lambda db: [ACC])
    monkeypatch.setattr(service, "campaigns", lambda db, a, d1, d2: CAMPAIGNS)
    monkeypatch.setattr(service, "approved_drafts", lambda db, a: [DRAFT])
    monkeypatch.setattr(service, "get_approval", lambda db, i: STATE["approval"] if i == 1 else None)
    monkeypatch.setattr(service, "approved_changes", lambda db, a: [STATE["approval"]])
    monkeypatch.setattr(service, "mark_executed", lambda db, i, result, by: STATE["marked"].append((i, result, by)))
    monkeypatch.setattr(service, "open_api_credentials", lambda db, a, http: STATE["creds"]())
    yield
    with session_scope() as db:
        db.execute(delete(Execution))
        db.execute(text("DELETE FROM audit_logs"))


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr(google, "assert_live_allowed", lambda db: None)


def test_status_reports_locked():
    with session_scope() as db:
        s = service.status(db)
    assert s["kill_switch"] is True and s["live_execution_allowed"] is False


def test_validate_records_row_and_audit_without_marking_executed():
    with session_scope() as db:
        r = service.validate(db, 1, by="me@x.com")
        assert r["status"] == "validated" and r["mode"] == "validate"
        assert _audit(db, "AND action = 'execution_validate_validated'") == 1
    assert STATE["marked"] == [] and json.loads(CALLS[0].content)["validateOnly"] is True


def test_execute_is_blocked_while_locked():
    with session_scope() as db:
        service.validate(db, 1, by="me")
        before = len(CALLS)
        with pytest.raises(FeatureDisabled):
            service.execute(db, 1, by="me", confirm="EXECUTE")
    assert len(CALLS) == before and STATE["marked"] == []


def test_execute_needs_confirmation_and_prior_validation(live):
    with session_scope() as db:
        with pytest.raises(ValidationFailed):
            service.execute(db, 1, by="me", confirm=None)
        with pytest.raises(ValidationFailed, match="Validate"):
            service.execute(db, 1, by="me", confirm="EXECUTE")
    assert CALLS == []


def test_validate_then_execute_then_rollback(live):
    with session_scope() as db:
        service.validate(db, 1, by="me")
        done = service.execute(db, 1, by="me", confirm="EXECUTE")
        assert done["status"] == "executed" and len(done["resource_names"]) == 3
        assert STATE["marked"][0][0] == 1
        live_body = json.loads(CALLS[-1].content)
        assert live_body["validateOnly"] is False and live_body["partialFailure"] is False
        with pytest.raises(ValidationFailed):
            service.rollback(db, done["id"], by="me", confirm=None)
        rb = service.rollback(db, done["id"], by="me", confirm="ROLLBACK")
        assert rb["status"] == "rolled_back" and rb["rollback_of"] == done["id"]
        ops = json.loads(CALLS[-1].content)["operations"]
        assert [o["remove"] for o in ops] == done["resource_names"]
        assert db.get(Execution, done["id"]).status == "rolled_back"
        with pytest.raises(ValidationFailed):
            service.rollback(db, done["id"], by="me", confirm="ROLLBACK")      # can't roll back twice
        assert _audit(db) == 3


def test_validation_must_match_the_current_plan(live):
    with session_scope() as db:
        service.validate(db, 1, by="me")
        STATE["approval"]["payload"] = {"negatives": NEG[:1]}              # the approved content changed afterwards
        with pytest.raises(ValidationFailed, match="Validate"):
            service.execute(db, 1, by="me", confirm="EXECUTE")


def test_google_rejection_is_recorded_and_nothing_marked_executed(live):
    def reject(req):
        body = json.loads(req.content)
        if body["validateOnly"]:
            return httpx.Response(200, json={})
        return httpx.Response(400, json={"error": {"details": [{"errors": [{"message": "Keyword text too long"}]}]}})

    STATE["creds"] = lambda: _creds(reject)
    with session_scope() as db:
        service.validate(db, 1, by="me")
        with pytest.raises(google.ExecutionFailed, match="too long"):
            service.execute(db, 1, by="me", confirm="EXECUTE")
        assert db.query(Execution).filter_by(mode="execute", status="failed").count() == 1
    assert STATE["marked"] == []


def test_only_approved_and_supported_changes_run():
    STATE["approval"]["status"] = "pending"
    with session_scope() as db:
        with pytest.raises(ValidationFailed, match="approved"):
            service.validate(db, 1, by="me")
    STATE["approval"].update(status="approved", change_type="bidding_change")
    with session_scope() as db:
        with pytest.raises(ValidationFailed, match="by hand"):
            service.validate(db, 1, by="me")
        rows = service.changes(db, 7)
    assert rows[0]["executable"] is False and "by hand" in rows[0]["reason"]
    assert CALLS == []


# ---- API ---------------------------------------------------------------------------------------------------

def _user(perms):
    return CurrentUser(id=1, email="me@example.com", name="me", role="x", permissions=frozenset(perms))


@pytest.fixture
def app():
    from app.main import create_app

    a = create_app()
    a.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    return a


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


B = "/api/v1/execution"


def test_api_read_only_users_can_look_but_not_act(client):
    assert client.get(f"{B}/status").json()["live_execution_allowed"] is False
    plan = client.get(f"{B}/approvals/1/plan").json()
    assert plan["operations"][0]["service"] == "campaignCriteria"
    assert client.post(f"{B}/approvals/1/validate").status_code == 403
    assert client.post(f"{B}/approvals/1/execute", json={"confirm": "EXECUTE"}).status_code == 403
    assert client.post(f"{B}/executions/1/rollback", json={"confirm": "ROLLBACK"}).status_code == 403
    assert CALLS == []


def test_api_execute_permission_still_cannot_go_live_while_locked(client, app):
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ, Permission.EXECUTE})
    assert client.post(f"{B}/approvals/1/validate").status_code == 200
    r = client.post(f"{B}/approvals/1/execute", json={"confirm": "EXECUTE"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "feature_disabled"
    assert all(json.loads(c.content)["validateOnly"] for c in CALLS)       # only validate-only traffic, ever
    ov = client.get(f"{B}/accounts/7").json()
    assert ov["changes"][0]["executable"] is True and ov["history"][0]["mode"] == "validate"


# ---- review hardening: no duplicate live changes ---------------------------------------------------------

def test_network_failure_after_send_blocks_any_second_execute(live):
    def drop(req):
        if json.loads(req.content)["validateOnly"]:
            return httpx.Response(200, json={})
        raise httpx.ReadTimeout("no answer")

    STATE["creds"] = lambda: _creds(drop)
    with session_scope() as db:
        service.validate(db, 1, by="me")
        with pytest.raises(service.UnknownOutcome):
            service.execute(db, 1, by="me", confirm="EXECUTE")
        assert db.query(Execution).filter_by(mode="execute", status="unknown").count() == 1
        STATE["creds"] = _creds                                     # Google is back — still must NOT send again
        before = len(CALLS)
        with pytest.raises(ValidationFailed, match="already executed"):
            service.execute(db, 1, by="me", confirm="EXECUTE")
        assert len(CALLS) == before


def test_second_execute_after_success_is_blocked_even_if_p16_marking_failed(live, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("p16 down")

    monkeypatch.setattr(service, "mark_executed", boom)
    with session_scope() as db:
        service.validate(db, 1, by="me")
        assert service.execute(db, 1, by="me", confirm="EXECUTE")["status"] == "executed"
        sent = len(CALLS)
        with pytest.raises(ValidationFailed, match="already executed"):
            service.execute(db, 1, by="me", confirm="EXECUTE")      # approval still says 'approved' in this fake
        assert len(CALLS) == sent


def test_rejected_execute_can_be_retried_after_fixing(live):
    def reject_once(req):
        if json.loads(req.content)["validateOnly"]:
            return httpx.Response(200, json={})
        return httpx.Response(400, json={"error": {"message": "nope"}})

    STATE["creds"] = lambda: _creds(reject_once)
    with session_scope() as db:
        service.validate(db, 1, by="me")
        with pytest.raises(google.ExecutionFailed):
            service.execute(db, 1, by="me", confirm="EXECUTE")
        STATE["creds"] = _creds
        assert service.execute(db, 1, by="me", confirm="EXECUTE")["status"] == "executed"   # 'failed' frees the claim


def test_rollback_refuses_foreign_resource_names_and_double_rollback(live):
    with session_scope() as db:
        service.validate(db, 1, by="me")
        done = service.execute(db, 1, by="me", confirm="EXECUTE")
        row = db.get(Execution, done["id"])
        row.resource_names = json.dumps(["customers/9999999999/campaignCriteria/1~2"])
        db.commit()
        with pytest.raises(ValidationFailed, match="don't belong"):
            service.rollback(db, done["id"], by="me", confirm="ROLLBACK")


def test_ids_must_be_numeric():
    with pytest.raises(plans.PlanError):
        plans.negatives_plan("123", [{"text": "x", "match_type": "EXACT", "campaign_id": "11/../99"}], CAMPAIGNS)
