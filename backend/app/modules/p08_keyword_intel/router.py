"""P08 — routes under /api/v1/keywords. Analysis + review only; nothing is sent to Google Ads."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p08_keyword_intel import service
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


class Window:
    def __init__(self, days: int = Query(default=90, ge=7, le=730)):
        self.d2 = date.today()
        self.d1 = self.d2 - timedelta(days=days - 1)


class ReviewIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=1000)
    status: str


@router.post("/accounts/{account_id}/analyze", dependencies=[Depends(verify_origin)])
def analyze(account_id: int, w: Window = Depends(), db: DbSession = Depends(get_db),
            _: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    return service.analyze(db, account_id, w.d1, w.d2)


@router.get("/accounts/{account_id}/negatives")
def negatives(account_id: int, status: str | None = None, min_confidence: float = Query(default=0, ge=0, le=1),
              db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.check_account(db, account_id)
    return service.list_negatives(db, account_id, status=status, min_confidence=min_confidence)


@router.post("/accounts/{account_id}/negatives/review", dependencies=[Depends(verify_origin)])
def review(account_id: int, body: ReviewIn, db: DbSession = Depends(get_db),
           user: CurrentUser = Depends(require_permission(Permission.APPROVE))) -> dict:
    return {"updated": service.review(db, account_id, body.ids, body.status, user.email)}


@router.get("/accounts/{account_id}/negatives/export", response_class=PlainTextResponse)
def export(account_id: int, fmt: str = Query(default="csv", pattern="^(csv|text)$"), db: DbSession = Depends(get_db),
           _: CurrentUser = READ) -> PlainTextResponse:
    body = service.negatives_export(db, account_id, fmt)
    headers = {"content-disposition": f'attachment; filename="negative-keywords-{account_id}.{"csv" if fmt == "csv" else "txt"}"'}
    return PlainTextResponse(body, media_type="text/csv" if fmt == "csv" else "text/plain", headers=headers)


@router.get("/accounts/{account_id}/classifications")
def classifications(account_id: int, intent: str | None = None, w: Window = Depends(), db: DbSession = Depends(get_db),
                    _: CurrentUser = READ) -> list[dict]:
    return service.classifications(db, account_id, w.d1, w.d2, intent)


@router.get("/accounts/{account_id}/insights")
def insights(account_id: int, w: Window = Depends(), db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.insights(db, account_id, w.d1, w.d2)
