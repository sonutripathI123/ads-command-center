"""Test bootstrap (owner: P00/P23). Tests run against a throwaway SQLite DB; no network."""
import os
import tempfile
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp(prefix="ads_cc_test_"))
os.environ.update({
    "APP_ENV": "test",
    "DATABASE_URL": f"sqlite:///{(_tmp / 'test.db').as_posix()}",
    "LOG_JSON": "false",
    "ADS_EXECUTION_KILL_SWITCH": "true",
})


@pytest.fixture(scope="session", autouse=True)
def _schema():
    import app.shared.feature_flags  # noqa: F401  register P00 table
    from app.shared.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    yield


@pytest.fixture
def db():
    from app.shared.db import session_scope

    with session_scope() as s:
        yield s
        s.rollback()


@pytest.fixture
def settings_override(monkeypatch):
    """Patch a Settings attribute for one test: settings_override(ads_execution_kill_switch=False)."""
    from app.shared.config import get_settings

    def _apply(**kwargs):
        s = get_settings()
        for k, v in kwargs.items():
            monkeypatch.setattr(s, k, v)
        return s

    return _apply
