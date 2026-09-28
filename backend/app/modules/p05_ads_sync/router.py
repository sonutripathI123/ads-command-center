"""P05 — routes under /api/v1/ads-sync. All data endpoints are read-only; POST /sync pulls from Google (read-only)."""
import json
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p04_ads_connection.interface import active_accounts
from app.modules.p05_ads_sync import service, sync
from app.modules.p05_ads_sync.models import SyncRun
from app.shared.db import get_db
from app.shared.errors import NotFoundError, ValidationFailed

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


class SyncIn(BaseModel):
    days: int | None = Field(default=None, ge=1, le=730, description="Full re-sync of the last N days")


def _run(r: SyncRun) -> dict:
    return {"id": r.id, "account_id": r.account_id, "status": r.status, "started_at": r.started_at,
            "finished_at": r.finished_at, "date_from": r.date_from, "date_to": r.date_to,
            "counts": json.loads(r.counts), "errors": json.loads(r.errors)}


def _window(date_from: date | None, date_to: date | None, days: int) -> tuple[date, date]:
    d2 = date_to or date.today()
    d1 = date_from or d2 - timedelta(days=days - 1)
    if d1 > d2:
        raise ValidationFailed("date_from is after date_to", module_id=sync.MODULE_ID)
    if (d2 - d1).days > 730:
        raise ValidationFailed("Date range is limited to 2 years", module_id=sync.MODULE_ID)
    return d1, d2


def _account(db: DbSession, account_id: int):
    acc = sync.find_account(db, account_id)
    if acc is None:
        raise NotFoundError("Ads account not found or not active", module_id=sync.MODULE_ID)
    return acc


class Window:
    def __init__(self, date_from: date | None = None, date_to: date | None = None,
                 days: int = Query(default=30, ge=1, le=730)):
        self.d1, self.d2 = _window(date_from, date_to, days)


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    out = []
    for a in active_accounts(db):
        last = service.runs(db, a.id, limit=1)
        out.append({"id": a.id, "customer_id": a.customer_id, "descriptive_name": a.descriptive_name,
                    "currency_code": a.currency_code, "time_zone": a.time_zone,
                    "last_run": _run(last[0]) if last else None})
    return out


@router.post("/accounts/{account_id}/sync", status_code=202, dependencies=[Depends(verify_origin)])
def start_sync(account_id: int, body: SyncIn, tasks: BackgroundTasks, db: DbSession = Depends(get_db),
               user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    acc = _account(db, account_id)
    if (existing := service.running(db, account_id)) is not None:
        return _run(existing)
    run = sync.start_run(db, acc, days=body.days, user_id=user.id)
    tasks.add_task(sync.execute_run, run.id)
    return _run(run)


@router.get("/accounts/{account_id}/runs")
def runs(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return [_run(r) for r in service.runs(db, account_id)]


@router.get("/accounts/{account_id}/summary")
def summary(account_id: int, w: Window = Depends(), db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    _account(db, account_id)
    return {"date_from": w.d1, "date_to": w.d2, **service.summary(db, account_id, w.d1, w.d2)}


@router.get("/accounts/{account_id}/campaigns")
def campaigns(account_id: int, w: Window = Depends(), db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return service.campaigns(db, account_id, w.d1, w.d2)


@router.get("/accounts/{account_id}/ad-groups")
def ad_groups(account_id: int, campaign_id: str | None = None, w: Window = Depends(), db: DbSession = Depends(get_db),
              _: CurrentUser = READ) -> list[dict]:
    return service.ad_groups(db, account_id, w.d1, w.d2, campaign_id)


@router.get("/accounts/{account_id}/keywords")
def keywords(account_id: int, campaign_id: str | None = None, ad_group_id: str | None = None, w: Window = Depends(),
             db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return service.keywords(db, account_id, w.d1, w.d2, campaign_id, ad_group_id)


@router.get("/accounts/{account_id}/search-terms")
def search_terms(account_id: int, q: str | None = Query(default=None, max_length=100), campaign_id: str | None = None,
                 limit: int = Query(default=500, ge=1, le=5000), w: Window = Depends(),
                 db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return service.search_terms(db, account_id, w.d1, w.d2, q=q, campaign_id=campaign_id, limit=limit)


@router.get("/accounts/{account_id}/ads")
def ads(account_id: int, w: Window = Depends(), db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return service.ads(db, account_id, w.d1, w.d2)
