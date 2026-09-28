"""P16 — routes under /api/v1/approvals. Deciding needs the approve permission; nothing is sent to Google Ads here."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p05_ads_sync.interface import list_accounts
from app.modules.p16_approvals import service
from app.shared.db import get_db
from app.shared.errors import NotFoundError, PermissionDenied

router = APIRouter()
READ = Depends(require_permission(Permission.READ))
STATUSES = ("pending", "approved", "rejected", "withdrawn", "executed")


class DecideIn(BaseModel):
    decision: str
    note: str | None = Field(default=None, max_length=2000)
    confirm: str | None = Field(default=None, max_length=32)


def _account(db: DbSession, account_id: int) -> None:
    if not any(a.id == account_id for a in list_accounts(db)):
        raise NotFoundError("Google Ads account not found", module_id=service.MODULE_ID)


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    out = []
    for a in list_accounts(db):
        rows = service.list_approvals(db, a.id, None)
        out.append({"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name,
                    "counts": {s: sum(r.status == s for r in rows) for s in STATUSES}})
    return out


@router.post("/accounts/{account_id}/sync", dependencies=[Depends(verify_origin)])
def sync(account_id: int, db: DbSession = Depends(get_db),
         user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    _account(db, account_id)
    return service.sync_queue(db, account_id, by=user.email)


@router.get("/accounts/{account_id}")
def list_(account_id: int, status: str | None = Query(default=None), db: DbSession = Depends(get_db),
          _: CurrentUser = READ) -> list[dict]:
    _account(db, account_id)
    return [service.approval_dict(db, a) for a in service.list_approvals(db, account_id, status)]


@router.get("/{approval_id}")
def get(approval_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.approval_dict(db, service.get(db, approval_id), with_history=True)


@router.post("/{approval_id}/decision", dependencies=[Depends(verify_origin)])
def decide(approval_id: int, body: DecideIn, db: DbSession = Depends(get_db),
           user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    if body.decision in ("approve", "reject") and not user.has(Permission.APPROVE):
        raise PermissionDenied("Approving or rejecting needs the approve permission", module_id=service.MODULE_ID)
    a = service.decide(db, approval_id, body.decision, by=user.email, note=body.note, confirm=body.confirm)
    return service.approval_dict(db, a, with_history=True)
