"""P22 — routes under /api/v1/security. Read-only: the audit log has no edit or delete endpoint anywhere."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission
from app.modules.p22_security_audit import service
from app.shared.db import get_db
from app.shared.errors import NotFoundError

router = APIRouter()
ADMIN = Depends(require_permission(Permission.ADMIN))


@router.get("/audit-logs")
def list_(module_id: str | None = Query(default=None), actor: str | None = Query(default=None),
          action: str | None = Query(default=None), entity_type: str | None = Query(default=None),
          entity_id: str | None = Query(default=None), since: date | None = Query(default=None),
          until: date | None = Query(default=None), limit: int = Query(default=50), offset: int = Query(default=0),
          db: DbSession = Depends(get_db), _: CurrentUser = ADMIN) -> dict:
    rows, total = service.query(db, module_id=module_id, actor=actor, action=action, entity_type=entity_type,
                                entity_id=entity_id, since=since, until=until, limit=limit, offset=offset)
    return {"rows": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/audit-logs/facets")
def facets(db: DbSession = Depends(get_db), _: CurrentUser = ADMIN) -> dict:
    return service.facets(db)


@router.get("/audit-logs/{log_id}")
def get(log_id: int, db: DbSession = Depends(get_db), _: CurrentUser = ADMIN) -> dict:
    row = service.get(db, log_id)
    if row is None:
        raise NotFoundError("Audit log entry not found", module_id=service.MODULE_ID)
    return row
