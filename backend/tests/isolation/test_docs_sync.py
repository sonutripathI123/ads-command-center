"""Governance: generated registry docs must match docs/modules.json; required governance files exist."""
import subprocess
import sys

import pytest

from ._helpers import BACKEND

pytestmark = pytest.mark.module("P00")
ROOT = BACKEND.parent
GOVERNANCE = ["MID.md", "PROJECT_MAP.md", "MODULE_REGISTRY.md", "DEPENDENCY_MAP.md", "CHANGE_PROTOCOL.md",
              "ARCHITECTURE.md", "SECURITY.md", "TESTING.md", "DECISIONS.md", "modules.json"]


@pytest.mark.parametrize("name", GOVERNANCE)
def test_governance_file_exists(name):
    assert (ROOT / "docs" / name).is_file()


def test_generated_tables_in_sync():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_registry.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
