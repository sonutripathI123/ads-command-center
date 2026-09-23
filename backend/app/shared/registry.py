"""SHARED (owner: P00) — typed access to docs/modules.json.

Public interface: load_registry, ModuleSpec, FlagSpec, Registry
"""
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.shared.config import get_settings


@dataclass(frozen=True)
class FlagSpec:
    key: str
    module_id: str
    default: bool
    description: str = ""
    kill_switch_guarded: bool = False


@dataclass(frozen=True)
class ModuleSpec:
    id: str
    name: str
    slug: str
    package: str
    status: str
    depends_on: tuple[str, ...]
    tables: tuple[str, ...]
    api_prefix: str | None
    may_mutate_google_ads: bool
    feature_flags: tuple[FlagSpec, ...] = field(default_factory=tuple)

    @property
    def is_active(self) -> bool:
        """Planned modules have no code; their routers are not mounted."""
        return self.status != "planned"


@dataclass(frozen=True)
class Registry:
    modules: tuple[ModuleSpec, ...]
    statuses: tuple[str, ...]

    def get(self, module_id: str) -> ModuleSpec:
        for m in self.modules:
            if m.id == module_id:
                return m
        raise KeyError(module_id)

    def by_package(self, package: str) -> ModuleSpec | None:
        return next((m for m in self.modules if m.package == package), None)

    @property
    def flags(self) -> dict[str, FlagSpec]:
        return {f.key: f for m in self.modules for f in m.feature_flags}


def parse_registry(path: Path) -> Registry:
    raw = json.loads(path.read_text(encoding="utf-8"))
    modules = tuple(
        ModuleSpec(
            id=m["id"], name=m["name"], slug=m["slug"], package=m["package"], status=m["status"],
            depends_on=tuple(m["depends_on"]), tables=tuple(m["tables"]), api_prefix=m["api_prefix"],
            may_mutate_google_ads=m["may_mutate_google_ads"],
            feature_flags=tuple(
                FlagSpec(key=f["key"], module_id=m["id"], default=f["default"],
                         description=f.get("description", ""), kill_switch_guarded=f.get("kill_switch_guarded", False))
                for f in m["feature_flags"]
            ),
        )
        for m in raw["modules"]
    )
    return Registry(modules=modules, statuses=tuple(raw["statuses"]))


@lru_cache
def load_registry() -> Registry:
    return parse_registry(get_settings().module_registry_path)
