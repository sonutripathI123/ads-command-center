"""P13 — routes under /api/v1/funnel. Read-only."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission
from app.modules.p13_booking_funnel import service
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


@router.get("/websites")
def websites(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return service.websites(db)


@router.get("/websites/{website_id}")
def website_funnel(website_id: int, date_from: date | None = Query(default=None), date_to: date | None = Query(default=None),
                   db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.website_funnel(db, website_id, date_from, date_to)
