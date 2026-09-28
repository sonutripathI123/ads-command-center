"""P09 — routes under /api/v1/creatives. Drafts only; nothing is published to Google Ads."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p05_ads_sync.interface import list_accounts
from app.modules.p09_ad_creative import service
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


class DraftIn(BaseModel):
    ad_group_name: str = Field(min_length=1, max_length=255)
    campaign_name: str = Field(default="", max_length=255)
    ad_group_google_id: str | None = Field(default=None, max_length=32)
    final_url: str = Field(default="", max_length=1024)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    usps: list[str] = Field(default_factory=list, max_length=20)
    use_ai: bool = True


class DraftPatch(BaseModel):
    headlines: list[str] | None = Field(default=None, max_length=20)
    descriptions: list[str] | None = Field(default=None, max_length=6)
    path1: str | None = Field(default=None, max_length=32)
    path2: str | None = Field(default=None, max_length=32)
    final_url: str | None = Field(default=None, max_length=1024)
    ad_group_name: str | None = Field(default=None, max_length=255)
    campaign_name: str | None = Field(default=None, max_length=255)
    usps: list[str] | None = Field(default=None, max_length=20)
    status: str | None = None


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return [{"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name, "ai_live": service.ai_live(db)}
            for a in list_accounts(db)]


@router.get("/accounts/{account_id}/analysis")
def analysis(account_id: int, days: int = Query(default=90, ge=7, le=365), db: DbSession = Depends(get_db),
             _: CurrentUser = READ) -> list[dict]:
    return service.analyse_existing(db, account_id, days)


@router.get("/accounts/{account_id}/ad-groups")
def ad_group_options(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return service.ad_group_options(db, account_id, 90)


@router.post("/accounts/{account_id}/drafts", status_code=201, dependencies=[Depends(verify_origin)])
def create(account_id: int, body: DraftIn, db: DbSession = Depends(get_db),
           user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    d = service.create_draft(db, account_id, ad_group_name=body.ad_group_name, campaign_name=body.campaign_name,
                             ad_group_google_id=body.ad_group_google_id, final_url=body.final_url, kw=body.keywords,
                             usps=body.usps, use_ai=body.use_ai, by=user.email)
    return service.draft_dict(db, d)


@router.get("/accounts/{account_id}/drafts")
def drafts(account_id: int, status: str | None = None, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.account(db, account_id)
    return [service.draft_dict(db, d) for d in service.list_drafts(db, account_id, status)]


@router.patch("/drafts/{draft_id}", dependencies=[Depends(verify_origin)])
def update(draft_id: int, body: DraftPatch, db: DbSession = Depends(get_db),
           user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    fields = body.model_dump(exclude_unset=True)
    if fields.get("status") == "approved" and not user.has(Permission.APPROVE):
        from app.shared.errors import PermissionDenied

        raise PermissionDenied("Approving an ad needs the approve permission", module_id=service.MODULE_ID)
    return service.draft_dict(db, service.update_draft(db, draft_id, fields, user.email))


@router.get("/accounts/{account_id}/drafts/export", response_class=PlainTextResponse)
def export(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> PlainTextResponse:
    service.account(db, account_id)
    return PlainTextResponse(service.export_csv(db, account_id), media_type="text/csv",
                             headers={"content-disposition": f'attachment; filename="rsa-drafts-{account_id}.csv"'})
