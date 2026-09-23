import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.modules.p02_auth import security
from app.modules.p02_auth.models import Session, User
from app.shared.db import Base, get_engine, session_scope

PASSWORD = "correct-horse-battery"


@pytest.fixture(scope="session", autouse=True)
def _p02_tables():
    Base.metadata.create_all(get_engine(), tables=[User.__table__, Session.__table__])


@pytest.fixture(autouse=True)
def _clean():
    security.throttle._fails.clear()
    yield
    with session_scope() as db:
        db.execute(delete(Session))
        db.execute(delete(User))


@pytest.fixture
def make_user():
    from app.modules.p02_auth.service import create_user

    def _make(email="admin@example.com", role="admin", execute=False):
        with session_scope() as db:
            u = create_user(db, email=email, name=email.split("@")[0], role=role, password=PASSWORD)
            u.execute_enabled = execute
            return u.id

    return _make


@pytest.fixture
def client():
    from app.main import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.fixture
def login(client):
    def _login(email="admin@example.com", password=PASSWORD):
        return client.post("/api/v1/auth/login", json={"email": email, "password": password})

    return _login
