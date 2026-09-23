"""P01 — Dashboard Shell contract tests (frontend is checked statically; no Node needed)."""
import json
import re
from pathlib import Path

import pytest

from app.shared.registry import load_registry

pytestmark = pytest.mark.module("P01")

FRONTEND = Path(__file__).resolve().parents[5] / "frontend"
SRC = FRONTEND / "src"
NAV = json.loads((SRC / "shell" / "nav.json").read_text(encoding="utf-8"))
ITEMS = [i for g in NAV["groups"] for i in g["items"]]

MID_SECTIONS = {  # MID §19
    "Overview", "Websites", "Ads Accounts", "Campaigns", "Ad Groups", "Keywords", "Search Terms",
    "Ads & Assets", "Conversions", "Bookings / Revenue", "Landing Pages", "Competitors", "AI Recommendations",
    "Campaign Builder", "Approval Center", "Monitoring & Alerts", "Reports", "Experiments", "Business Rules",
    "Audit Log", "Settings",
}
IMPORT_RE = re.compile(r"""(?:import|export)[^'"]*?from\s+['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)""")


def _ts_files(root: Path):
    return [p for p in root.rglob("*") if p.suffix in {".ts", ".tsx"} and p.is_file()]


def _imports(path: Path):
    return [a or b for a, b in IMPORT_RE.findall(path.read_text(encoding="utf-8"))]


def test_nav_covers_exactly_mid_sections():
    assert {i["label"] for i in ITEMS} == MID_SECTIONS


def test_nav_slugs_unique():
    slugs = [i["slug"] for i in ITEMS]
    assert len(slugs) == len(set(slugs))


def test_nav_module_ids_registered():
    ids = {m.id for m in load_registry().modules}
    assert all(i["moduleId"] in ids for i in ITEMS)


def test_shell_does_not_import_feature_modules():
    bad = [f"{f}: {i}" for f in _ts_files(SRC / "shell") for i in _imports(f) if i.startswith("@/modules")]
    assert not bad, bad


def test_shell_only_calls_foundation_api():
    for f in _ts_files(SRC / "shell"):
        for path in re.findall(r"/api/v1/[a-z-]+", f.read_text(encoding="utf-8")):
            assert path == "/api/v1/foundation", f"{f} calls {path}; the shell must not call module APIs"


def test_feature_modules_use_public_interfaces_only():
    mods = SRC / "modules"
    if not mods.exists():
        pytest.skip("no frontend feature modules yet")
    bad = []
    for f in _ts_files(mods):
        own = f.relative_to(mods).parts[0]
        for i in _imports(f):
            if i.startswith("@/shell") and i != "@/shell":
                bad.append(f"{f}: {i} (use '@/shell')")
            m = re.match(r"@/modules/([^/]+)(/.*)?$", i)
            if m and m[1] != own and m[2]:
                bad.append(f"{f}: {i} (use '@/modules/{m[1]}')")
    assert not bad, "\n".join(bad)


def test_no_remote_fonts_or_hardcoded_secrets():
    for f in _ts_files(SRC):
        text = f.read_text(encoding="utf-8")
        assert "next/font/google" not in text, f"{f}: remote fonts break offline builds"
        assert not re.search(r"(api[_-]?key|secret|developer[_-]?token)\s*[:=]\s*['\"][^'\"]{8,}", text, re.I), f
