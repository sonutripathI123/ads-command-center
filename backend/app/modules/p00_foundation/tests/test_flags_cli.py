import pytest

from app.shared.feature_flags import FeatureFlagOverride, is_enabled
from app.shared.flags_cli import main

pytestmark = pytest.mark.module("P00")


@pytest.fixture(autouse=True)
def _clean(db):
    yield
    from sqlalchemy import delete

    from app.shared.db import session_scope

    with session_scope() as s:
        s.execute(delete(FeatureFlagOverride))


def _state(key):
    from app.shared.db import session_scope

    with session_scope() as s:
        row = s.get(FeatureFlagOverride, key)
        return (is_enabled(key, s), row.reason if row else None, row.updated_by if row else None)


def test_set_on_off_and_clear(capsys):
    assert main(["set", "crawler.enabled", "on", "--reason", "scan own sites", "--by", "ops@example.com"]) == 0
    assert _state("crawler.enabled") == (True, "scan own sites", "ops@example.com")
    assert main(["set", "crawler.enabled", "off", "--reason", "pause"]) == 0
    assert _state("crawler.enabled")[0] is False
    assert main(["clear", "crawler.enabled"]) == 0
    assert _state("crawler.enabled") == (False, None, None)


def test_list_shows_flags(capsys):
    assert main(["list"]) == 0
    assert "crawler.enabled" in capsys.readouterr().out


def test_unknown_flag_rejected():
    assert main(["set", "crawler.enabeld", "on", "--reason", "x"]) == 2


def test_execution_flags_cannot_be_changed():
    assert main(["set", "ads.execution.enabled", "on", "--reason", "x"]) == 3
    assert _state("ads.execution.enabled") == (False, None, None)


def test_reason_required():
    with pytest.raises(SystemExit):
        main(["set", "crawler.enabled", "on"])
    assert main(["set", "crawler.enabled", "on", "--reason", "   "]) == 2
