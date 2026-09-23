"""Isolation: code must respect module boundaries declared in docs/modules.json.

Rules enforced:
  1. Every package under app/modules is registered; every active module has a package + governance docs.
  2. A module may import another module ONLY via `app.modules.<pkg>.interface`, and only if declared in depends_on.
  3. app/shared never imports app.modules.
  4. Only P17 code may call Google Ads mutate APIs.
  5. Every mounted route lives under an active module's api_prefix.
  6. Every ORM table defined by a module is declared as owned by that module.
"""
import importlib
import re

import pytest

from app.shared.db import Base
from app.shared.registry import load_registry

from ._helpers import MODULES_DIR, SHARED_DIR, imported_names, owning_package, py_files

pytestmark = pytest.mark.module("P00")
R = load_registry()
REQUIRED_DOCS = ["MODULE.md", "OWNERSHIP.md", "TESTS.md", "CHANGELOG.md"]


def _packages_on_disk():
    return sorted(p.name for p in MODULES_DIR.iterdir() if p.is_dir() and p.name != "__pycache__")


def test_no_unregistered_module_packages():
    registered = {m.package for m in R.modules}
    unknown = set(_packages_on_disk()) - registered
    assert not unknown, f"unregistered module packages: {unknown}"


@pytest.mark.parametrize("spec", [m for m in R.modules if m.is_active], ids=lambda m: m.id)
def test_active_module_has_package_and_docs(spec):
    pkg = MODULES_DIR / spec.package
    assert pkg.is_dir(), f"{spec.id} is {spec.status} but {pkg} is missing"
    for doc in REQUIRED_DOCS:
        assert (pkg / doc).is_file(), f"{spec.id} missing {doc}"
    assert (pkg / "interface.py").is_file(), f"{spec.id} missing interface.py"
    assert (pkg / "tests").is_dir(), f"{spec.id} missing tests/"
    if spec.api_prefix:
        assert (pkg / "router.py").is_file(), f"{spec.id} has api_prefix but no router.py"


_MOD_IMPORT = re.compile(r"^app\.modules\.(?P<pkg>[a-z0-9_]+)(?P<rest>(\.[A-Za-z0-9_]+)*)$")


def _boundary_violations():
    out = []
    for f in py_files(MODULES_DIR):
        if f.parent == MODULES_DIR:
            continue
        own = R.by_package(owning_package(f))
        for name in imported_names(f):
            m = _MOD_IMPORT.match(name)
            if not m or m["pkg"] == own.package:
                continue
            target = R.by_package(m["pkg"])
            rest = m["rest"].lstrip(".")
            if target is None:
                out.append(f"{f}: imports unknown module {name}")
            elif target.id not in own.depends_on:
                out.append(f"{f}: {own.id} imports {target.id} which is not in its depends_on")
            elif rest and not (rest == "interface" or rest.startswith("interface.")):
                out.append(f"{f}: imports {name}; cross-module imports must go through .interface")
    return out


def test_cross_module_imports_respect_dependency_map():
    assert not _boundary_violations(), "\n".join(_boundary_violations())


def test_shared_never_imports_modules():
    bad = [f"{f}: {n}" for f in py_files(SHARED_DIR) for n in imported_names(f) if n.startswith("app.modules")]
    assert not bad, "\n".join(bad)


_MUTATE = re.compile(r"\.mutate\w*\(|MutateOperation|mutate_operations")


def test_only_p17_calls_google_ads_mutations():
    p17 = R.get("P17").package
    offenders = []
    for f in py_files(MODULES_DIR) + py_files(SHARED_DIR):
        if "tests" in f.parts:
            continue
        if f.is_relative_to(MODULES_DIR) and f.parent != MODULES_DIR and owning_package(f) == p17:
            continue
        if _MUTATE.search(f.read_text(encoding="utf-8")):
            offenders.append(str(f))
    assert not offenders, f"Google Ads mutation calls outside P17: {offenders}"


def test_routes_belong_to_active_modules():
    from app.main import create_app

    prefixes = [m.api_prefix for m in R.modules if m.is_active and m.api_prefix]
    paths = list(create_app().openapi()["paths"])
    assert paths, "no API routes found"
    for path in paths:
        assert any(path == p or path.startswith(p + "/") for p in prefixes), f"route {path} has no owning module"


def test_orm_tables_declared_by_owner():
    import app.shared.feature_flags  # noqa: F401

    for spec in R.modules:
        if spec.is_active and (MODULES_DIR / spec.package / "models.py").is_file():
            importlib.import_module(f"app.modules.{spec.package}.models")
    owner = {t: m.id for m in R.modules for t in m.tables}
    undeclared = [t for t in Base.metadata.tables if t not in owner]
    assert not undeclared, f"tables not declared in docs/modules.json: {undeclared}"
