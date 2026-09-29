"""P19 — routes under /api/v1/reports."""
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p19_reports import service
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


class GenerateIn(BaseModel):
    scope: str
    scope_id: int
    period: str = "weekly"
    date_from: date | None = None
    date_to: date | None = None


@router.get("/options")
def options(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.scopes(db)


@router.get("/runs")
def runs(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return [service.run_dict(r, full=False) for r in service.list_runs(db)]


@router.post("/runs", status_code=201, dependencies=[Depends(verify_origin)])
def generate(body: GenerateIn, db: DbSession = Depends(get_db), user: CurrentUser = READ) -> dict:
    """Any signed-in user may generate a report (it only reads data)."""
    return service.run_dict(service.generate(db, scope=body.scope, scope_id=body.scope_id, period=body.period,
                                             d1=body.date_from, d2=body.date_to, by=user.email))


@router.get("/runs/{report_id}")
def get(report_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.run_dict(service.get(db, report_id))


@router.get("/runs/{report_id}/csv", response_class=PlainTextResponse)
def csv(report_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> PlainTextResponse:
    return PlainTextResponse(service.csv_text(service.get(db, report_id)), media_type="text/csv",
                             headers={"content-disposition": f'attachment; filename="report-{report_id}.csv"'})


@router.get("/runs/{report_id}/html", response_class=HTMLResponse)
def html(report_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> HTMLResponse:
    return HTMLResponse(service.html_text(service.get(db, report_id)))
