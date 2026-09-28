"""P14 — routes under /api/v1/recommendations."""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p05_ads_sync.interface import list_accounts
from app.modules.p14_recommendations import service
from app.modules.p14_recommendations.models import AIRun
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


class StatusIn(BaseModel):
    status: str
    note: str | None = Field(default=None, max_length=1000)


def _run(r: AIRun | None) -> dict | None:
    if r is None:
        return None
    return {"id": r.id, "mode": r.mode, "model": r.model, "status": r.status, "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens, "plan": json.loads(r.output) if r.output else None, "error": r.error,
            "created_by": r.created_by, "created_at": r.created_at}


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return [{"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name,
             "open": sum(1 for r in service.list_recs(db, a.id) if r.status == "proposed")} for a in list_accounts(db)]


@router.get("/ai-status")
def ai_status(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.ai_status(db)


@router.post("/accounts/{account_id}/refresh", dependencies=[Depends(verify_origin)])
def refresh(account_id: int, db: DbSession = Depends(get_db),
            _: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    return service.refresh(db, account_id)


@router.get("/accounts/{account_id}")
def list_recs(account_id: int, status: str | None = None, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.account(db, account_id)
    return [service.rec_dict(r) for r in service.list_recs(db, account_id, status)]


@router.post("/{rec_id}/status", dependencies=[Depends(verify_origin)])
def set_status(rec_id: int, body: StatusIn, db: DbSession = Depends(get_db),
               user: CurrentUser = Depends(require_permission(Permission.APPROVE))) -> dict:
    return service.rec_dict(service.set_status(db, rec_id, body.status, by=user.email, note=body.note))


@router.post("/accounts/{account_id}/plan", dependencies=[Depends(verify_origin)])
def plan(account_id: int, db: DbSession = Depends(get_db),
         user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    return _run(service.generate_plan(db, account_id, by=user.email))


@router.get("/accounts/{account_id}/plan")
def latest_plan(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    service.account(db, account_id)
    return {"run": _run(service.latest_plan(db, account_id))}
