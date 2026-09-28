"""P07 — routes under /api/v1/audit."""
import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p05_ads_sync.interface import list_accounts
from app.modules.p07_ppc_audit import service
from app.modules.p07_ppc_audit.models import AuditIssue, AuditRun
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


class RunIn(BaseModel):
    days: int = Field(default=90, ge=7, le=365)


class StatusIn(BaseModel):
    status: str
    note: str | None = Field(default=None, max_length=1000)


def _run(r: AuditRun | None) -> dict | None:
    if r is None:
        return None
    return {"id": r.id, "ads_account_id": r.ads_account_id, "website_id": r.website_id, "days": r.days, "score": r.score,
            "counts": json.loads(r.counts), "errors": json.loads(r.errors), "triggered_by": r.triggered_by, "created_at": r.created_at}


def _issue(i: AuditIssue) -> dict:
    return {"id": i.id, "module_id": "P07", "code": i.code, "category": i.category, "severity": i.severity, "title": i.title,
            "observation": i.observation, "evidence": json.loads(i.evidence), "reasoning": i.reasoning, "proposed_action": i.action,
            "expected_impact": i.impact, "confidence": i.confidence, "risk": i.risk, "entity_type": i.entity_type,
            "entity_id": i.entity_id, "link": i.link, "status": i.status, "dismissed_by": i.dismissed_by,
            "dismiss_note": i.dismiss_note, "requires_approval": False}


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    out = []
    for a in list_accounts(db):
        last = service.history(db, a.id, limit=1)
        out.append({"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name, "last_audit": _run(last[0] if last else None)})
    return out


@router.post("/accounts/{account_id}/run", dependencies=[Depends(verify_origin)])
def run(account_id: int, body: RunIn, db: DbSession = Depends(get_db),
        user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    return _run(service.run_audit(db, account_id, body.days, by=user.email))


@router.get("/accounts/{account_id}/latest")
def latest(account_id: int, include_dismissed: bool = Query(default=False), db: DbSession = Depends(get_db),
           _: CurrentUser = READ) -> dict:
    service.account(db, account_id)
    r, issues = service.latest(db, account_id)
    return {"run": _run(r), "issues": [_issue(i) for i in issues if include_dismissed or i.status == "open"],
            "dismissed": sum(1 for i in issues if i.status == "dismissed")}


@router.get("/accounts/{account_id}/history")
def history(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.account(db, account_id)
    return [_run(r) for r in service.history(db, account_id)]


@router.post("/issues/{issue_id}/status", dependencies=[Depends(verify_origin)])
def set_status(issue_id: int, body: StatusIn, db: DbSession = Depends(get_db),
               user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    return _issue(service.set_status(db, issue_id, body.status, by=user.email, note=body.note))
