"""Governance: every migration names its owning module and has rollback notes; chain applies cleanly."""
import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from app.shared.registry import load_registry

from ._helpers import BACKEND

pytestmark = pytest.mark.module("P00")
VERSIONS = BACKEND / "alembic" / "versions"
MIGRATIONS = sorted(p for p in VERSIONS.glob("*.py") if p.name != "__init__.py")


def _module_id(path: Path) -> str | None:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "module_id" for t in node.targets):
            return ast.literal_eval(node.value)
    return None


@pytest.mark.parametrize("path", MIGRATIONS, ids=lambda p: p.name)
def test_migration_declares_owner_and_rollback_notes(path):
    mid = _module_id(path)
    assert mid in {m.id for m in load_registry().modules}, f"{path.name}: module_id={mid!r} is not a registered module"
    text = path.read_text(encoding="utf-8")
    assert "Rollback/recovery notes:" in text and "DESCRIBE HERE" not in text, f"{path.name}: missing rollback notes"


def test_upgrade_and_downgrade_round_trip():
    db = Path(tempfile.mkdtemp()) / "mig.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db.as_posix()}"}
    for args in (["upgrade", "head"], ["downgrade", "base"], ["upgrade", "head"]):
        r = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
