"""P06 — routes under /api/v1/conversions."""
import json
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p03_website_intel.interface import list_websites
from app.modules.p06_analytics import service
from app.modules.p06_analytics.models import AnalyticsSyncRun
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


def _run(r: AnalyticsSyncRun | None) -> dict | None:
    if r is None:
        return None
    return {"id": r.id, "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at,
            "date_from": r.date_from, "date_to": r.date_to, "counts": json.loads(r.counts), "errors": json.loads(r.errors)}


class SyncIn(BaseModel):
    days: int = Field(default=90, ge=1, le=480)


class MappingIn(BaseModel):
    event_name: str = Field(min_length=1, max_length=128)
    role: str


class ImportIn(BaseModel):
    csv: str = Field(min_length=1, max_length=5_000_000)
    default_website_id: int | None = None


def _window(days: int) -> tuple[date, date]:
    d2 = date.today() - timedelta(days=1)
    return d2 - timedelta(days=days - 1), d2


@router.get("/websites")
def websites(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    out = []
    for w in list_websites(db):
        last = service.runs(db, w.id, limit=1)
        out.append({"id": w.id, "name": w.name, "domain": w.domain, "ga4_property_id": w.ga4_property_id,
                    "gsc_site_url": w.gsc_site_url, "ads_account_id": w.ads_account_id,
                    "last_run": _run(last[0] if last else None)})
    return out


@router.post("/websites/{website_id}/sync", status_code=202, dependencies=[Depends(verify_origin)])
def sync(website_id: int, body: SyncIn, tasks: BackgroundTasks, db: DbSession = Depends(get_db),
         _: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    run, created = service.start_sync(db, service.website(db, website_id), body.days)
    if created:
        tasks.add_task(service.execute_sync, run.id)
    return _run(run)


@router.get("/websites/{website_id}/runs")
def runs(website_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.website(db, website_id)
    return [_run(r) for r in service.runs(db, website_id)]


@router.get("/websites/{website_id}/overview")
def overview(website_id: int, days: int = Query(default=30, ge=1, le=480), db: DbSession = Depends(get_db),
             _: CurrentUser = READ) -> dict:
    d1, d2 = _window(days)
    return service.overview(db, service.website(db, website_id), d1, d2)


@router.put("/websites/{website_id}/mappings", dependencies=[Depends(verify_origin)])
def mapping(website_id: int, body: MappingIn, db: DbSession = Depends(get_db),
            user: CurrentUser = Depends(require_permission(Permission.APPROVE))) -> dict:
    service.website(db, website_id)
    m = service.set_mapping(db, website_id, body.event_name, body.role, user.email)
    return {"event_name": m.event_name, "role": m.role}


@router.post("/bookings/import", dependencies=[Depends(verify_origin)])
def import_bookings(body: ImportIn, db: DbSession = Depends(get_db),
                    _: CurrentUser = Depends(require_permission(Permission.APPROVE))) -> dict:
    return service.import_bookings(db, body.csv, default_website_id=body.default_website_id)


@router.get("/bookings/summary")
def bookings(days: int = Query(default=90, ge=1, le=730), website_id: int | None = None,
             db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    d1, d2 = _window(days)
    return service.bookings_summary(db, d1, d2 + timedelta(days=1), website_id)
