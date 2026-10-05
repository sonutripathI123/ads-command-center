"""P12 — routes under /api/v1/budget-bid. Reads Google Ads (SELECT only); advice only, nothing is changed anywhere."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p04_ads_connection.interface import active_accounts
from app.modules.p12_budget_bid import service
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


class RunIn(BaseModel):
    days: int = Field(default=90, ge=14, le=365)


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return [{"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name, "last_run": service.last_run(db, a.id)}
            for a in active_accounts(db)]


@router.get("/accounts/{account_id}/latest")
def latest(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    service.account(db, account_id)
    return service.latest(db, account_id) or {"run": None, "findings": [], "tables": None}


@router.post("/accounts/{account_id}/run", dependencies=[Depends(verify_origin)])
def run(account_id: int, body: RunIn, db: DbSession = Depends(get_db),
        user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    return service.run(db, account_id, body.days, by=user.email)
