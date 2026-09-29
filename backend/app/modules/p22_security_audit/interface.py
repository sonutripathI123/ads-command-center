"""P22 — public interface. Any module that mutates something security-sensitive calls `record()`.

    from app.modules.p22_security_audit.interface import record

    record(db, module_id="P16", action="approval_approved", actor=user.email, actor_role=user.role,
           entity_type="approval", entity_id=a.id, before={"status": "pending"}, after={"status": "approved"}, commit=False)

Pass `commit=False` when the caller's own transaction will commit afterwards (typical — one commit per request).
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p22_security_audit import service
from app.modules.p22_security_audit.models import AuditLog

__all__ = ["record"]


def record(db: DbSession, *, module_id: str, action: str, actor: str | None = None, actor_role: str | None = None,
           entity_type: str | None = None, entity_id: int | str | None = None, before=None, after=None,
           note: str | None = None, request_id: str | None = None, ip: str | None = None, commit: bool = True) -> AuditLog:
    return service.record(db, module_id=module_id, action=action, actor=actor, actor_role=actor_role, entity_type=entity_type,
                          entity_id=entity_id, before=before, after=after, note=note, request_id=request_id, ip=ip, commit=commit)
