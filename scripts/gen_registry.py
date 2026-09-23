"""Regenerate the tables in docs/MODULE_REGISTRY.md and docs/DEPENDENCY_MAP.md from docs/modules.json.

Only content between <!-- GENERATED:START --> and <!-- GENERATED:END --> is replaced;
hand-written text around it is preserved.

    python scripts/gen_registry.py          # rewrite
    python scripts/gen_registry.py --check  # exit 1 if out of date (used by tests)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
START, END = "<!-- GENERATED:START -->", "<!-- GENERATED:END -->"


def _load():
    return json.loads((DOCS / "modules.json").read_text(encoding="utf-8"))["modules"]


def registry_table(mods) -> str:
    rows = ["| ID | Module | Status | Backend package | API prefix | Tables | Flags |",
            "|---|---|---|---|---|---|---|"]
    for m in mods:
        rows.append(
            f"| {m['id']} | {m['name']} | `{m['status']}` | `backend/app/modules/{m['package']}/` "
            f"| {('`' + m['api_prefix'] + '`') if m['api_prefix'] else '—'} "
            f"| {', '.join(m['tables']) or '—'} | {', '.join(f['key'] for f in m['feature_flags']) or '—'} |"
        )
    return "\n".join(rows)


def dependency_table(mods) -> str:
    by_id = {m["id"]: m for m in mods}
    used_by = {m["id"]: [] for m in mods}
    for m in mods:
        for d in m["depends_on"]:
            used_by[d].append(m["id"])
    rows = ["| Module | May depend on (via `interface.py`) | Depended on by | May mutate Google Ads |",
            "|---|---|---|---|"]
    for m in mods:
        deps = ", ".join(f"{d} {by_id[d]['name']}" for d in m["depends_on"]) or "— (shared only)"
        rows.append(f"| {m['id']} {m['name']} | {deps} | {', '.join(used_by[m['id']]) or '—'} "
                    f"| {'**YES — gated**' if m['may_mutate_google_ads'] else 'no'} |")
    return "\n".join(rows)


def _splice(path: Path, body: str) -> str:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(f"{path} is missing generated markers")
    return pattern.sub(lambda _: f"{START}\n{body}\n{END}", text)


def main(check: bool) -> int:
    mods = _load()
    targets = {DOCS / "MODULE_REGISTRY.md": registry_table(mods), DOCS / "DEPENDENCY_MAP.md": dependency_table(mods)}
    stale = []
    for path, body in targets.items():
        new = _splice(path, body)
        if new != path.read_text(encoding="utf-8"):
            stale.append(path.name)
            if not check:
                path.write_text(new, encoding="utf-8")
    if check and stale:
        print(f"out of date: {', '.join(stale)} — run python scripts/gen_registry.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
