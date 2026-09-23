"""Governance: docs/modules.json must be internally consistent."""
import pytest

from app.shared.registry import load_registry

pytestmark = pytest.mark.module("P00")
R = load_registry()


def test_ids_are_p00_to_p24_in_order():
    assert [m.id for m in R.modules] == [f"P{i:02d}" for i in range(25)]


@pytest.mark.parametrize("attr", ["slug", "package"])
def test_unique(attr):
    values = [getattr(m, attr) for m in R.modules]
    assert len(values) == len(set(values))


def test_api_prefixes_unique_and_versioned():
    prefixes = [m.api_prefix for m in R.modules if m.api_prefix]
    assert len(prefixes) == len(set(prefixes))
    assert all(p.startswith("/api/v1/") for p in prefixes)


def test_statuses_valid():
    assert all(m.status in R.statuses for m in R.modules)


def test_dependencies_exist_and_acyclic():
    ids = {m.id for m in R.modules}
    graph = {m.id: set(m.depends_on) for m in R.modules}
    for mid, deps in graph.items():
        assert mid not in deps, f"{mid} depends on itself"
        assert deps <= ids, f"{mid} has unknown deps {deps - ids}"

    visiting, done = set(), set()

    def visit(n, path):
        assert n not in visiting, f"dependency cycle: {' -> '.join(path + [n])}"
        if n in done:
            return
        visiting.add(n)
        for d in graph[n]:
            visit(d, path + [n])
        visiting.discard(n)
        done.add(n)

    for n in graph:
        visit(n, [])


def test_each_table_has_exactly_one_owner():
    seen = {}
    for m in R.modules:
        for t in m.tables:
            assert t not in seen, f"table {t} owned by both {seen[t]} and {m.id}"
            seen[t] = m.id


def test_flag_keys_unique_and_default_off():
    keys = [f.key for m in R.modules for f in m.feature_flags]
    assert len(keys) == len(set(keys))
    assert all(f.default is False for m in R.modules for f in m.feature_flags)


def test_only_p17_may_mutate_google_ads():
    assert [m.id for m in R.modules if m.may_mutate_google_ads] == ["P17"]


def test_kill_switch_guarded_flags_belong_to_p17():
    guarded = {f.module_id for m in R.modules for f in m.feature_flags if f.kill_switch_guarded}
    assert guarded == {"P17"}
