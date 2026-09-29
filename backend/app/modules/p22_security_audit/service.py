"""P22 — audit log: any module calls `record()` to append one immutable entry. Never edited or deleted from the API;
the only way rows leave the table is the module's own migration downgrade."""
import json
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.modules.p22_security_audit.models import AuditLog

MODULE_ID = "P22"
MAX_NOTE = 4000


def record(db: DbSession, *, module_id: str, action: str, actor: str | None = None, actor_role: str | None = None,
           entity_type: str | None = None, entity_id: int | str | None = None, before=None, after=None,
           note: str | None = None, request_id: str | None = None, ip: str | None = None, commit: bool = True) -> AuditLog:
    row = AuditLog(module_id=module_id, action=action[:64], actor=actor, actor_role=actor_role,
                   entity_type=entity_type, entity_id=str(entity_id) if entity_id is not None else None,
                   before=json.dumps(before, default=str), after=json.dumps(after, default=str),
                   note=(note or "")[:MAX_NOTE] or None, request_id=request_id, ip=ip)
    db.add(row)
    if commit:
        db.commit()
    else:
        db.flush()
    return row


def _dict(r: AuditLog) -> dict:
    return {"id": r.id, "at": r.at, "module_id": r.module_id, "action": r.action, "actor": r.actor, "actor_role": r.actor_role,
            "entity_type": r.entity_type, "entity_id": r.entity_id, "before": json.loads(r.before), "after": json.loads(r.after),
            "note": r.note, "request_id": r.request_id, "ip": r.ip}


def query(db: DbSession, *, module_id: str | None = None, actor: str | None = None, action: str | None = None,
         entity_type: str | None = None, entity_id: str | None = None, since: date | None = None, until: date | None = None,
         limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    limit = max(1, min(limit, 200))
    stmt = select(AuditLog)
    if module_id:
        stmt = stmt.where(AuditLog.module_id == module_id)
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == str(entity_id))
    if since:
        stmt = stmt.where(AuditLog.at >= datetime.combine(since, datetime.min.time()))
    if until:
        stmt = stmt.where(AuditLog.at < datetime.combine(until, datetime.min.time()))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(AuditLog.at.desc(), AuditLog.id.desc()).offset(offset).limit(limit)).all()
    return [_dict(r) for r in rows], total


def get(db: DbSession, log_id: int) -> dict | None:
    r = db.get(AuditLog, log_id)
    return _dict(r) if r else None


def facets(db: DbSession) -> dict:
    modules = [x for x, in db.execute(select(AuditLog.module_id).distinct().order_by(AuditLog.module_id))]
    actions = [x for x, in db.execute(select(AuditLog.action).distinct().order_by(AuditLog.action))]
    return {"modules": modules, "actions": actions}
