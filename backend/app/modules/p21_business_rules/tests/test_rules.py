import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p21_business_rules.models import BusinessRule, BusinessRuleVersion
from app.modules.p21_business_rules.rules import Rules
from app.shared.db import Base, get_engine, session_scope

pytestmark = pytest.mark.module("P21")
B = "/api/v1/business-rules"


def _user(role, perms):
    return CurrentUser(id=1, email=f"{role}@example.com", name=role, role=role, permissions=frozenset(perms))


APPROVER = _user("approver", {Permission.READ, Permission.RECOMMEND, Permission.APPROVE})
VIEWER = _user("viewer", {Permission.READ})


@pytest.fixture(scope="module", autouse=True)
def _tables():
    Base.metadata.create_all(get_engine(), tables=[BusinessRule.__table__, BusinessRuleVersion.__table__])


@pytest.fixture(autouse=True)
def _clean():
    yield
    with session_scope() as db:
        db.execute(delete(BusinessRuleVersion))
        db.execute(delete(BusinessRule))


@pytest.fixture
def app():
    from app.main import create_app

    a = create_app()
    a.dependency_overrides[get_current_user] = lambda: APPROVER
    return a


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def test_rules_normalise_lists():
    r = Rules(excluded_terms=["  Jobs ", "jobs", "CHEAP  price", ""])
    assert r.excluded_terms == ["jobs", "cheap price"]


def test_defaults_are_chauffeur_specific():
    r = Rules()
    assert "airport transfer" in r.services and "melbourne" in r.locations and "uber" in r.excluded_terms
    assert "sydney" in r.other_locations


def test_get_returns_defaults_when_nothing_saved(client):
    r = client.get(B).json()
    assert r["version"] == 0 and r["is_default"] and r["scope"] == "global"


def test_save_creates_versions_and_skips_unchanged(client):
    rules = client.get(B).json()["rules"]
    rules["excluded_terms"].append("pizza")
    r1 = client.put(B, json={"rules": rules, "note": "add pizza"}).json()
    assert r1["version"] == 1 and "pizza" in r1["rules"]["excluded_terms"] and r1["updated_by"] == "approver@example.com"
    assert client.put(B, json={"rules": rules}).json()["version"] == 1  # unchanged → no new version
    rules["target_cost_per_conversion"] = 80
    assert client.put(B, json={"rules": rules}).json()["version"] == 2
    assert [v["version"] for v in client.get(f"{B}/versions").json()] == [2, 1]


def test_restore_old_version(client):
    rules = client.get(B).json()["rules"]
    rules["brand_terms"] = ["corporate cars melbourne"]
    client.put(B, json={"rules": rules})
    rules["brand_terms"] = []
    client.put(B, json={"rules": rules})
    r = client.post(f"{B}/versions/1/restore").json()
    assert r["version"] == 3 and r["rules"]["brand_terms"] == ["corporate cars melbourne"] and r["note"] == "restored v1"


def test_account_scope_overrides_global(client):
    from app.modules.p21_business_rules.interface import get_rules

    g = client.get(B).json()["rules"]
    g["locations"] = ["melbourne"]
    client.put(B, json={"rules": g})
    a = dict(g, locations=["geelong"])
    client.put(f"{B}?account_id=7", json={"rules": a})
    with session_scope() as db:
        assert get_rules(db, 7).locations == ["geelong"]
        assert get_rules(db, 8).locations == ["melbourne"]
        assert get_rules(db).locations == ["melbourne"]


def test_viewer_cannot_save(client, app):
    app.dependency_overrides[get_current_user] = lambda: VIEWER
    assert client.get(B).status_code == 200
    assert client.put(B, json={"rules": Rules().model_dump()}).status_code == 403


def test_validation(client):
    assert client.put(B, json={"rules": {"min_clicks_for_negative": 0}}).status_code == 422
