"""P00 — Foundation & Governance routes (read-only).

GET /api/v1/foundation/health    liveness + DB connectivity
GET /api/v1/foundation/modules   module registry (id, name, status, dependencies)
GET /api/v1/foundation/flags     resolved feature flags

There is intentionally no flag-write endpoint: that requires P02 auth and a P22 audit trail.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.p00_foundation.schemas import FlagOut, HealthOut, ModuleOut
from app.shared.config import get_settings
from app.shared.db import get_db
from app.shared.feature_flags import resolve_all
from app.shared.logging import get_logger
from app.shared.registry import load_registry

MODULE_ID = "P00"
log = get_logger(MODULE_ID)
router = APIRouter()


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        log.exception("health_db_failed")
        db_ok = False
    settings = get_settings()
    return HealthOut(status="ok" if db_ok else "degraded", database=db_ok, env=settings.app_env,
                     execution_kill_switch=settings.ads_execution_kill_switch)


@router.get("/modules", response_model=list[ModuleOut])
def modules() -> list[ModuleOut]:
    return [ModuleOut(id=m.id, name=m.name, slug=m.slug, status=m.status, depends_on=list(m.depends_on),
                      api_prefix=m.api_prefix) for m in load_registry().modules]


@router.get("/flags", response_model=list[FlagOut])
def flags(db: Session = Depends(get_db)) -> list[FlagOut]:
    return [FlagOut(**s.__dict__) for s in resolve_all(db)]
