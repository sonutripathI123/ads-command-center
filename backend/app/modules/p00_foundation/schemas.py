"""P00 — response contracts. Changing these is an API contract change (docs/CHANGE_PROTOCOL.md §API)."""
from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str
    database: bool
    env: str
    execution_kill_switch: bool


class ModuleOut(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    depends_on: list[str]
    api_prefix: str | None


class FlagOut(BaseModel):
    key: str
    module_id: str
    enabled: bool
    source: str
    description: str
