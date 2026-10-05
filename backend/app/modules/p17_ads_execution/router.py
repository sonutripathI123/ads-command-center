"""P17 — routes under /api/v1/execution. Viewing is read-only; every action needs the per-user EXECUTE permission
(granted only via the server CLI), and live actions are additionally blocked while the kill switch / flag are off."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p04_ads_connection.interface import active_accounts
from app.modules.p16_approvals.interface import approved_changes
from app.modules.p17_ads_execution import service
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))
EXECUTE = Depends(require_permission(Permission.EXECUTE))


class ConfirmIn(BaseModel):
    confirm: str | None = Field(default=None, max_length=32)


@router.get("/status")
def status(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.status(db)


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return [{"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name,
             "approved_waiting": len(approved_changes(db, a.id))} for a in active_accounts(db)]


@router.get("/accounts/{account_id}")
def overview(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return {"status": service.status(db), "changes": service.changes(db, account_id), "history": service.history(db, account_id)}


@router.get("/approvals/{approval_id}/plan")
def plan(approval_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.preview(db, approval_id)


@router.post("/approvals/{approval_id}/validate", dependencies=[Depends(verify_origin)])
def validate(approval_id: int, db: DbSession = Depends(get_db), user: CurrentUser = EXECUTE) -> dict:
    return service.validate(db, approval_id, by=user.email)


@router.post("/approvals/{approval_id}/execute", dependencies=[Depends(verify_origin)])
def execute(approval_id: int, body: ConfirmIn, db: DbSession = Depends(get_db), user: CurrentUser = EXECUTE) -> dict:
    return service.execute(db, approval_id, by=user.email, confirm=body.confirm)


@router.post("/executions/{execution_id}/rollback", dependencies=[Depends(verify_origin)])
def rollback(execution_id: int, body: ConfirmIn, db: DbSession = Depends(get_db), user: CurrentUser = EXECUTE) -> dict:
    return service.rollback(db, execution_id, by=user.email, confirm=body.confirm)


@router.get("/history")
def history(account_id: int = Query(), db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return service.history(db, account_id)
