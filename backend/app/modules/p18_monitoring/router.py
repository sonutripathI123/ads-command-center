"""P18 — routes under /api/v1/monitoring. Checks only read data; nothing is changed in Google Ads."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p18_monitoring import service
from app.shared.db import get_db
from app.shared.feature_flags import is_enabled

router = APIRouter()
READ = Depends(require_permission(Permission.READ))
RECOMMEND = Depends(require_permission(Permission.RECOMMEND))


class StatusIn(BaseModel):
    status: str


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return {"scheduled_enabled": is_enabled(service.SCHEDULE_FLAG, db),
            "accounts": [{"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name,
                          "open": {s: sum(x.severity == s for x in service.alerts(db, a.id)) for s in ("critical", "warning", "info")}}
                         for a in service.list_accounts(db)]}


@router.get("/accounts/{account_id}")
def overview(account_id: int, status: str | None = Query(default=None), db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    service.account(db, account_id)
    return {"alerts": [service.alert_dict(a) for a in service.alerts(db, account_id, status)],
            "runs": [service.run_dict(r) for r in service.runs(db, account_id)]}


@router.post("/accounts/{account_id}/run", dependencies=[Depends(verify_origin)])
def run(account_id: int, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    return service.run_dict(service.run(db, account_id, trigger="manual", by=user.email))


@router.post("/alerts/{alert_id}/status", dependencies=[Depends(verify_origin)])
def set_status(alert_id: int, body: StatusIn, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    return service.alert_dict(service.set_status(db, alert_id, body.status, by=user.email))
