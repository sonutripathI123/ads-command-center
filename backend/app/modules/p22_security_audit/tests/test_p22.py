"""P22 tests: the audit log itself (service) and the read-only API."""
import pytest
from fastapi.testclient import TestClient

from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user
from app.modules.p22_security_audit import service
from app.modules.p22_security_audit.models import AuditLog

pytestmark = pytest.mark.module("P22")


def test_record_serializes_before_after(db):
    row = service.record(db, module_id="P16", action="approval_approved", actor="a@x.com", actor_role="admin",
                         entity_type="approval", entity_id=7, before={"status": "pending"}, after={"status": "approved"},
                         note="looks good", commit=False)
    assert row.id is not None
    got = service.get(db, row.id)
    assert got == {"id": row.id, "at": row.at, "module_id": "P16", "action": "approval_approved", "actor": "a@x.com",
                   "actor_role": "admin", "entity_type": "approval", "entity_id": "7", "before": {"status": "pending"},
                   "after": {"status": "approved"}, "note": "looks good", "request_id": None, "ip": None}


def test_record_defaults_and_missing(db):
    row = service.record(db, module_id="P09", action="ad_draft_approved", entity_id=3, commit=False)
    got = service.get(db, row.id)
    assert got["before"] is None and got["after"] is None and got["actor"] is None
    assert service.get(db, 999999) is None


def test_query_filters(db):
    # entity_type is namespaced to this test so counts are unaffected by audit rows other test suites commit for real.
    service.record(db, module_id="P16", action="approval_approved", actor="qa+p22a@example.com", entity_type="p22test_approval",
                   entity_id=1, commit=False)
    service.record(db, module_id="P16", action="approval_rejected", actor="qa+p22b@example.com", entity_type="p22test_approval",
                   entity_id=2, commit=False)
    service.record(db, module_id="P09", action="ad_draft_approved", actor="qa+p22a@example.com", entity_type="p22test_ad_draft",
                   entity_id=5, commit=False)
    rows, total = service.query(db, module_id="P16", entity_type="p22test_approval")
    assert total == 2 and {r["action"] for r in rows} == {"approval_approved", "approval_rejected"}
    rows, total = service.query(db, actor="qa+p22a@example.com", entity_type="p22test_approval")
    assert total == 1
    rows, total = service.query(db, entity_type="p22test_approval", entity_id="2")
    assert total == 1 and rows[0]["action"] == "approval_rejected"
    rows, total = service.query(db, entity_type="p22test_approval", limit=1)
    assert len(rows) == 1 and total == 2


def test_facets(db):
    service.record(db, module_id="P16", action="approval_approved", entity_id=1, commit=False)
    service.record(db, module_id="P09", action="ad_draft_rejected", entity_id=2, commit=False)
    f = service.facets(db)
    assert set(f["modules"]) >= {"P09", "P16"} and set(f["actions"]) >= {"approval_approved", "ad_draft_rejected"}


# ---- API ----------------------------------------------------------------------------------------------

def _user(perms):
    return CurrentUser(id=1, email="me@example.com", name="me", role="x", permissions=frozenset(perms))


@pytest.fixture
def app():
    from app.main import create_app

    a = create_app()
    a.dependency_overrides[get_current_user] = lambda: _user({Permission.READ, Permission.ADMIN})
    return a


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


B = "/api/v1/security"


def test_api_list_get_facets_and_permissions(client, app, db):
    service.record(db, module_id="P16", action="approval_approved", actor="a@x.com", entity_type="approval", entity_id=1)
    db.commit()
    r = client.get(f"{B}/audit-logs").json()
    assert r["total"] >= 1 and r["rows"][0]["module_id"] == "P16"
    row_id = r["rows"][0]["id"]
    assert client.get(f"{B}/audit-logs/{row_id}").json()["action"] == "approval_approved"
    assert client.get(f"{B}/audit-logs/999999999").status_code == 404
    facets = client.get(f"{B}/audit-logs/facets").json()
    assert "P16" in facets["modules"]
    app.dependency_overrides[get_current_user] = lambda: _user({Permission.READ})
    assert client.get(f"{B}/audit-logs").status_code == 403
