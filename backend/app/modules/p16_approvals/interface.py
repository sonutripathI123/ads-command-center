"""P16 — public interface (for P17 execution, P19 reports, P20 experiments and any module that needs a human decision).

    from app.modules.p16_approvals.interface import request_approval, get_approval, approved_changes, mark_executed
"""
from datetime import date

from sqlalchemy.orm import Session as DbSession

from app.modules.p16_approvals import service
from app.modules.p16_approvals.models import Approval

__all__ = ["request_approval", "get_approval", "approved_changes", "mark_executed", "decisions"]


def request_approval(db: DbSession, *, account_id: int, source_module: str, source_ref: str, change_type: str, title: str,
                     before: dict, after: dict, evidence: list, risk: str, payload: dict, requested_by: str | None) -> dict:
    """Queue a change for a human decision. Idempotent per open source_ref. Commits."""
    a = service.request_approval(db, account_id=account_id, source_module=source_module, source_ref=source_ref,
                                 change_type=change_type, title=title, before=before, after=after, evidence=evidence,
                                 risk=risk, payload=payload, requested_by=requested_by)
    db.commit()
    return service.approval_dict(db, a)


def get_approval(db: DbSession, approval_id: int) -> dict | None:
    a = db.get(Approval, approval_id)
    return service.approval_dict(db, a) if a else None


def approved_changes(db: DbSession, account_id: int) -> list[dict]:
    """Approved, not yet executed — the only list P17 may execute from (oldest first)."""
    return [service.approval_dict(db, a) for a in reversed(service.list_approvals(db, account_id, "approved"))]


def decisions(db: DbSession, account_id: int, d1: date, d2: date) -> list[dict]:
    """Requests decided (approved/rejected/withdrawn/executed) between d1 and d2 inclusive — for P19 reports."""
    out = []
    for a in service.list_approvals(db, account_id, None):
        when = a.decided_at or a.executed_at
        if when and d1 <= when.date() <= d2 and a.status != "pending":
            out.append({"id": a.id, "title": a.title, "change_type": a.change_type, "status": a.status, "impact": a.impact,
                        "decided_by": a.decided_by, "decided_at": when})
    return out


def mark_executed(db: DbSession, approval_id: int, *, result: str, by: str) -> dict:
    return service.approval_dict(db, service.mark_executed(db, approval_id, result=result, by=by))
