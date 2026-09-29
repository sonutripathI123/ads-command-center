"""P10 — routes under /api/v1/landing-pages. Reads the business's own pages; nothing is changed on the sites or in Google Ads."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p10_landing_cro import rules, service
from app.shared.db import get_db
from app.shared.feature_flags import is_enabled

router = APIRouter()
READ = Depends(require_permission(Permission.READ))
RECOMMEND = Depends(require_permission(Permission.RECOMMEND))


class BriefIn(BaseModel):
    use_ai: bool = True


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return {"fetch_enabled": is_enabled(service.FETCH_FLAG, db), "ai_live": service.ai_live(db), "categories": rules.CATEGORIES,
            "accounts": [{"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name,
                          "landing_urls": len(service.landing_contexts(db, a.id)), "runs": service.runs(db, a.id)[:1]}
                         for a in service.list_accounts(db)]}


@router.post("/accounts/{account_id}/check", dependencies=[Depends(verify_origin)])
def check(account_id: int, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    key = service.run_check(db, account_id, by=user.email)
    return {"run_key": key, "pages": [service.check_dict(db, c) for c in service.checks(db, account_id, key)]}


@router.get("/accounts/{account_id}")
def latest(account_id: int, run: str | None = Query(default=None, max_length=32), db: DbSession = Depends(get_db),
           _: CurrentUser = READ) -> dict:
    service.account(db, account_id)
    return {"runs": service.runs(db, account_id), "pages": [service.check_dict(db, c) for c in service.checks(db, account_id, run)]}


@router.get("/checks/{check_id}")
def get_check(check_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.check_dict(db, service.get_check(db, check_id), full=True)


@router.post("/checks/{check_id}/brief", status_code=201, dependencies=[Depends(verify_origin)])
def brief(check_id: int, body: BriefIn, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    return service.brief_dict(service.create_brief(db, check_id, use_ai=body.use_ai, by=user.email))


@router.get("/briefs/{brief_id}")
def get_brief(brief_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.brief_dict(service.get_brief(db, brief_id))


@router.get("/briefs/{brief_id}/markdown", response_class=PlainTextResponse)
def brief_md(brief_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> PlainTextResponse:
    return PlainTextResponse(service.brief_markdown(service.get_brief(db, brief_id)), media_type="text/markdown",
                             headers={"content-disposition": f'attachment; filename="landing-brief-{brief_id}.md"'})
