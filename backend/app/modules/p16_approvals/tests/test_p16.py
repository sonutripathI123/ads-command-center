"""P16 tests. Source modules replaced through their public interfaces."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p16_approvals import interface, router, service
from app.modules.p16_approvals.models import Approval, ApprovalEvent
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P16")

ACC = SimpleNamespace(id=7, customer_id="1949408641", descriptive_name="CCM")
SRC: dict[str, list] = {}


def _rec(i, category="bidding", status="accepted", requires=True):
    return {"id": i, "category": category, "status": status, "requires_approval": requires, "title": f"Rec {i}",
            "observation": "obs", "proposed_action": "do it", "evidence": [["Cost", "AUD 10"]], "risk": "medium",
            "entity_type": "campaign", "entity_id": "1"}


def _neg(i, text):
    return {"id": i, "text": text, "match_type": "PHRASE", "level": "account", "campaign_google_id": None,
            "cost": 5.0, "clicks": 2, "conversions": 0}


AD = {"id": 3, "ad_group_name": "Airport", "campaign_name": "C", "headlines": ["H1"], "descriptions": ["D1"],
      "final_url": "https://x.com.au/", "path1": "a", "path2": "b", "strength": 90, "mode": "ai", "model": "claude-opus-5"}
CAMP = {"id": 4, "name": "CCM | Search", "settings": {"daily_budget": 30, "bidding": {"strategy": "MAXIMIZE_CLICKS"}},
        "ad_groups": [{"name": "Airport", "keywords": [1, 2]}], "negatives": [1], "checklist": [{"label": "Ads", "status": "pass"}]}


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[Approval.__table__, ApprovalEvent.__table__])


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    SRC.update(recs=[_rec(1), _rec(2, "keywords"), _rec(3, status="proposed"), _rec(4, requires=False)],
               negs=[_neg(10, "jobs"), _neg(11, "uber")], ads=[AD], camps=[CAMP])
    monkeypatch.setattr(service, "open_recommendations", lambda db, a: SRC["recs"])
    monkeypatch.setattr(service, "accepted_negatives", lambda db, a: SRC["negs"])
    monkeypatch.setattr(service, "approved_drafts", lambda db, a: SRC["ads"])
    monkeypatch.setattr(service, "approved_campaign_drafts", lambda db, a: SRC["camps"])
    monkeypatch.setattr(router, "list_accounts", lambda db: [ACC])
    yield
    with session_scope() as db:
        db.execute(delete(ApprovalEvent))
        db.execute(delete(Approval))


def _user(perms, email="me@example.com"):
    return CurrentUser(id=1, email=email, name="me", role="x", permissions=frozenset(perms))


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


B = "/api/v1/approvals"


def _items(client, **q):
    return client.get(f"{B}/accounts/7", params=q).json()


def test_sync_collects_sources_and_is_idempotent(client):
    r = client.post(f"{B}/accounts/7/sync")
    assert r.status_code == 200 and r.json() == {"created": 5, "withdrawn": 0}
    items = {i["source_ref"].split("|")[0] + "|" + i["change_type"]: i for i in _items(client)}
    assert set(items) == {"P14|bidding_change", "P14|keyword_change", "P08|add_negative_keywords", "P09|create_rsa",
                          "P15|create_campaign"}
    assert items["P14|bidding_change"]["impact"] == "high" and items["P14|keyword_change"]["impact"] == "standard"
    assert items["P15|create_campaign"]["impact"] == "high" and items["P15|create_campaign"]["confirm_required"] == "APPROVE"
    neg = items["P08|add_negative_keywords"]
    assert neg["after"]["negatives"] == ['"jobs"', '"uber"'] and neg["payload"]["negative_ids"] == [10, 11]
    assert items["P09|create_rsa"]["after"]["headlines"] == ["H1"]
    assert client.post(f"{B}/accounts/7/sync").json() == {"created": 0, "withdrawn": 0}
    SRC["negs"].append(_neg(12, "didi"))  # a newly accepted negative → a second, smaller batch
    assert client.post(f"{B}/accounts/7/sync").json()["created"] == 1
    batches = [i for i in _items(client) if i["change_type"] == "add_negative_keywords"]
    assert sorted(len(b["payload"]["negative_ids"]) for b in batches) == [1, 2]


def test_sync_withdraws_when_source_no_longer_approved(client):
    client.post(f"{B}/accounts/7/sync")
    SRC["ads"], SRC["recs"] = [], [_rec(2, "keywords")]
    assert client.post(f"{B}/accounts/7/sync").json() == {"created": 0, "withdrawn": 2}
    st = {i["source_ref"]: i["status"] for i in _items(client)}
    assert st["P09|ad|3"] == "withdrawn" and st["P14|rec|1"] == "withdrawn" and st["P14|rec|2"] == "pending"
    assert st[next(k for k in st if k.startswith("P08"))] == "pending"  # negatives are never auto-withdrawn


def test_decisions_confirmation_and_history(client):
    client.post(f"{B}/accounts/7/sync")
    items = {i["change_type"]: i for i in _items(client)}
    rsa, camp = items["create_rsa"], items["create_campaign"]
    r = client.post(f"{B}/{rsa['id']}/decision", json={"decision": "approve"})
    assert r.status_code == 200 and r.json()["status"] == "approved" and r.json()["decided_by"] == "me@example.com"
    assert [h["event"] for h in r.json()["history"]] == ["requested", "approved"]
    assert client.post(f"{B}/{rsa['id']}/decision", json={"decision": "approve"}).status_code == 422  # already decided
    r = client.post(f"{B}/{camp['id']}/decision", json={"decision": "approve"})
    assert r.status_code == 422 and "APPROVE" in r.text
    r = client.post(f"{B}/{camp['id']}/decision", json={"decision": "approve", "confirm": "APPROVE"})
    assert r.status_code == 403  # own high-impact request without a note
    r = client.post(f"{B}/{camp['id']}/decision", json={"decision": "approve", "confirm": "APPROVE", "note": "reviewed checklist"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    neg = items["add_negative_keywords"]
    assert client.post(f"{B}/{neg['id']}/decision", json={"decision": "reject"}).status_code == 422  # reason required
    assert client.post(f"{B}/{neg['id']}/decision", json={"decision": "reject", "note": "keep uber"}).json()["status"] == "rejected"
    assert client.post(f"{B}/{rsa['id']}/decision", json={"decision": "nope"}).status_code == 422
    assert client.get(f"{B}/999999").status_code == 404
    counts = next(a for a in client.get(f"{B}/accounts").json() if a["id"] == 7)["counts"]
    assert counts["approved"] == 2 and counts["rejected"] == 1 and counts["pending"] == 2
    assert {i["id"] for i in _items(client, status="approved")} == {rsa["id"], camp["id"]}


def test_interface_request_approved_and_executed(client):
    with session_scope() as db:
        a = interface.request_approval(db, account_id=7, source_module="P20", source_ref="P20|exp|1", change_type="start_experiment",
                                       title="Start test", before={}, after={"x": 1}, evidence=[], risk="low", payload={"e": 1},
                                       requested_by="me@example.com")
        again = interface.request_approval(db, account_id=7, source_module="P20", source_ref="P20|exp|1", change_type="start_experiment",
                                           title="Start test", before={}, after={}, evidence=[], risk="low", payload={}, requested_by=None)
        assert again["id"] == a["id"] and a["status"] == "pending" and a["impact"] == "standard"
        assert interface.approved_changes(db, 7) == []
        with pytest.raises(Exception):
            interface.mark_executed(db, a["id"], result="ok", by="P17")
    client.post(f"{B}/{a['id']}/decision", json={"decision": "approve"})
    with session_scope() as db:
        assert [c["id"] for c in interface.approved_changes(db, 7)] == [a["id"]]
        done = interface.mark_executed(db, a["id"], result="created 1 ad", by="P17")
        assert done["status"] == "executed" and done["execution_result"] == "created 1 ad"
        assert interface.approved_changes(db, 7) == [] and interface.get_approval(db, 999999) is None


def test_permissions_and_withdraw(client, app):
    client.post(f"{B}/accounts/7/sync")
    item = _items(client)[0]
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ, Permission.RECOMMEND})
    assert client.post(f"{B}/{item['id']}/decision", json={"decision": "approve"}).status_code == 403
    r = client.post(f"{B}/{item['id']}/decision", json={"decision": "withdraw", "note": "not now"})
    assert r.status_code == 200 and r.json()["status"] == "withdrawn"
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert client.post(f"{B}/accounts/7/sync").status_code == 403
    assert client.get(f"{B}/accounts/7").status_code == 200
    assert client.get(f"{B}/accounts/99").status_code == 404
