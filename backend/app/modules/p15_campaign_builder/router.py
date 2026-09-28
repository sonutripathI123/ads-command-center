"""P15 — routes under /api/v1/campaign-builder. Drafts only; nothing is created in Google Ads."""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p03_website_intel.interface import list_websites
from app.modules.p05_ads_sync.interface import ad_groups, keywords, list_accounts
from app.modules.p15_campaign_builder import builder, service
from app.shared.db import get_db
from app.shared.errors import PermissionDenied

router = APIRouter()
READ = Depends(require_permission(Permission.READ))


class BuildIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    goal: str = Field(default="", max_length=2000)
    source_ad_groups: list[str] = Field(default_factory=list, max_length=200)
    website_id: int | None = None
    themes: list[str] | None = None
    daily_budget: float = Field(default=30.0, ge=1, le=10_000)
    max_cpc: float = Field(default=3.0, ge=0.1, le=100)


class EditIn(BaseModel):
    op: str
    model_config = {"extra": "allow"}


class WriteAdsIn(BaseModel):
    usps: list[str] = Field(default_factory=list, max_length=20)
    use_ai: bool = True


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    from datetime import date, timedelta

    d2 = date.today()
    d1 = d2 - timedelta(days=89)
    sites = list_websites(db)
    out = []
    for a in list_accounts(db):
        counts: dict[str, int] = {}
        for k in keywords(db, a.id, d1, d2):
            counts[k["ad_group_google_id"]] = counts.get(k["ad_group_google_id"], 0) + 1
        groups = [{"google_id": g["google_id"], "name": g["name"], "campaign_name": g["campaign_name"], "status": g["status"],
                   "keywords": counts.get(g["google_id"], 0)} for g in ad_groups(db, a.id, d1, d2)]
        out.append({"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name,
                    "websites": [{"id": w.id, "name": w.name, "domain": w.domain} for w in sites if w.ads_account_id == a.id],
                    "ad_groups": sorted(groups, key=lambda g: -g["keywords"]),
                    "themes": [{"key": k, "label": label} for k, label, _ in builder.THEMES]})
    return out


@router.post("/accounts/{account_id}/drafts", status_code=201, dependencies=[Depends(verify_origin)])
def build(account_id: int, body: BuildIn, db: DbSession = Depends(get_db),
          user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    d = service.build(db, account_id, name=body.name, goal=body.goal, source_ad_groups=body.source_ad_groups,
                      website_id=body.website_id, themes=body.themes, daily_budget=body.daily_budget, max_cpc=body.max_cpc,
                      by=user.email)
    return service.draft_dict(db, d)


@router.get("/accounts/{account_id}/drafts")
def drafts(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.account(db, account_id)
    return [{"id": d.id, "name": d.name, "status": d.status, "created_at": d.created_at, "created_by": d.created_by}
            for d in service.list_drafts(db, account_id)]


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.draft_dict(db, service.get(db, draft_id))


@router.patch("/drafts/{draft_id}", dependencies=[Depends(verify_origin)])
def edit(draft_id: int, body: EditIn, db: DbSession = Depends(get_db),
         user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    op = body.model_dump()
    if op.get("op") == "status" and op.get("status") == "approved" and not user.has(Permission.APPROVE):
        raise PermissionDenied("Approving a campaign needs the approve permission", module_id=service.MODULE_ID)
    return service.draft_dict(db, service.edit(db, draft_id, op, user.email))


@router.post("/drafts/{draft_id}/ad-groups/{group_key}/write-ads", dependencies=[Depends(verify_origin)])
def write_ads(draft_id: int, group_key: str, body: WriteAdsIn, db: DbSession = Depends(get_db),
              user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    return service.draft_dict(db, service.write_ads(db, draft_id, group_key, usps=body.usps, use_ai=body.use_ai, by=user.email))


@router.get("/drafts/{draft_id}/export", response_class=PlainTextResponse)
def export(draft_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> PlainTextResponse:
    return PlainTextResponse(service.export_csv(db, draft_id), media_type="text/csv",
                             headers={"content-disposition": f'attachment; filename="campaign-draft-{draft_id}.csv"'})
