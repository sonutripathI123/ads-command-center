import pytest

from app.shared.config import get_settings
from app.shared.errors import FeatureDisabled
from app.shared.feature_flags import FeatureFlagOverride, UnknownFlagError, is_enabled, require_enabled, resolve

pytestmark = pytest.mark.module("P00")


def test_unknown_flag_raises():
    with pytest.raises(UnknownFlagError):
        is_enabled("crawler.enabeld")


def test_default_used_without_db():
    s = resolve("crawler.enabled")
    assert (s.enabled, s.source, s.module_id) == (False, "default", "P03")


def test_db_override_applies(db):
    db.add(FeatureFlagOverride(key="crawler.enabled", enabled=True, reason="test"))
    db.flush()
    s = resolve("crawler.enabled", db)
    assert (s.enabled, s.source) == (True, "override")


def test_kill_switch_beats_db_override(db):
    assert get_settings().ads_execution_kill_switch is True
    db.add(FeatureFlagOverride(key="ads.execution.enabled", enabled=True))
    db.flush()
    s = resolve("ads.execution.enabled", db)
    assert (s.enabled, s.source) == (False, "kill_switch")


def test_execution_needs_both_switch_off_and_override(db, settings_override):
    settings_override(ads_execution_kill_switch=False)
    assert is_enabled("ads.execution.enabled", db) is False  # still default off
    db.add(FeatureFlagOverride(key="ads.execution.enabled", enabled=True))
    db.flush()
    assert is_enabled("ads.execution.enabled", db) is True


def test_require_enabled_raises_feature_disabled():
    with pytest.raises(FeatureDisabled) as e:
        require_enabled("ads.execution.enabled", None, module_id="P17")
    assert e.value.details == {"flag": "ads.execution.enabled", "source": "kill_switch"}


def test_secrets_not_in_repr():
    s = get_settings()
    assert "dev-only-change-me" not in repr(s)
