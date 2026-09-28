"""P03 — routes under /api/v1/websites."""
import json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p03_website_intel import service
from app.modules.p03_website_intel.extract import ISSUE_LABELS
from app.modules.p03_website_intel.models import CrawlRun, Page, Website
from app.modules.p05_ads_sync.interface import list_accounts
from app.shared.db import get_db
from app.shared.feature_flags import is_enabled

router = APIRouter()
READ = Depends(require_permission(Permission.READ))
EDIT = Depends(require_permission(Permission.APPROVE))


class WebsiteIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=3, max_length=255)
    primary_service: str = Field(default="", max_length=128)
    location: str = Field(default="", max_length=128)
    time_zone: str = Field(default="Australia/Melbourne", max_length=64)
    ads_account_id: int | None = None
    ga4_property_id: str | None = Field(default=None, max_length=32)
    gsc_site_url: str | None = Field(default=None, max_length=512)
    notes: str = Field(default="", max_length=5000)


class WebsitePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    primary_service: str | None = Field(default=None, max_length=128)
    location: str | None = Field(default=None, max_length=128)
    time_zone: str | None = Field(default=None, max_length=64)
    ads_account_id: int | None = None
    ga4_property_id: str | None = Field(default=None, max_length=32)
    gsc_site_url: str | None = Field(default=None, max_length=512)
    notes: str | None = Field(default=None, max_length=5000)
    status: str | None = None


class CrawlIn(BaseModel):
    max_pages: int = Field(default=50, ge=1, le=300)


def _run(r: CrawlRun | None) -> dict | None:
    if r is None:
        return None
    return {"id": r.id, "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at,
            "max_pages": r.max_pages, "pages_found": r.pages_found, "pages_crawled": r.pages_crawled,
            "source": r.source, "errors": json.loads(r.errors)}


def _site(db: DbSession, w: Website, accounts: dict) -> dict:
    ps = service.pages(db, w.id)
    last = service.runs(db, w.id, limit=1)
    acc = accounts.get(w.ads_account_id)
    return {"id": w.id, "name": w.name, "domain": w.domain, "base_url": w.base_url, "primary_service": w.primary_service,
            "location": w.location, "time_zone": w.time_zone, "ads_account_id": w.ads_account_id,
            "ads_account_label": (acc.descriptive_name or acc.customer_id) if acc else None,
            "ads_customer_id": acc.customer_id if acc else None, "ga4_property_id": w.ga4_property_id,
            "gsc_site_url": w.gsc_site_url, "notes": w.notes, "status": w.status, "created_at": w.created_at,
            "pages": len(ps), "pages_with_issues": sum(1 for p in ps if json.loads(p.issues)),
            "last_crawl": _run(last[0] if last else None)}


def _page(p: Page) -> dict:
    return {"id": p.id, "url": p.url, "status_code": p.status_code, "final_url": p.final_url, "title": p.title,
            "meta_description": p.meta_description, "h1": p.h1, "word_count": p.word_count, "response_ms": p.response_ms,
            "services": json.loads(p.services), "locations": json.loads(p.locations), "issues": json.loads(p.issues),
            "has_form": p.has_form, "has_phone": p.has_phone, "cta_count": p.cta_count, "last_crawled_at": p.last_crawled_at}


def _accounts(db: DbSession) -> dict:
    return {a.id: a for a in list_accounts(db)}


@router.get("/meta")
def meta(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return {"crawler_enabled": is_enabled(service.CRAWL_FLAG, db), "issue_labels": ISSUE_LABELS,
            "ads_accounts": [{"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name} for a in list_accounts(db)]}


@router.get("")
def list_sites(include_archived: bool = False, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    accs = _accounts(db)
    return [_site(db, w, accs) for w in service.list_websites(db, include_archived)]


@router.post("", status_code=201, dependencies=[Depends(verify_origin)])
def create(body: WebsiteIn, db: DbSession = Depends(get_db), _: CurrentUser = EDIT) -> dict:
    w = service.create_website(db, **body.model_dump())
    return _site(db, w, _accounts(db))


@router.get("/{website_id}")
def get_site(website_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return _site(db, service.get_website(db, website_id), _accounts(db))


@router.patch("/{website_id}", dependencies=[Depends(verify_origin)])
def update(website_id: int, body: WebsitePatch, db: DbSession = Depends(get_db), _: CurrentUser = EDIT) -> dict:
    w = service.update_website(db, website_id, body.model_dump(exclude_unset=True))
    return _site(db, w, _accounts(db))


@router.post("/{website_id}/crawl", status_code=202, dependencies=[Depends(verify_origin)])
def crawl(website_id: int, body: CrawlIn, tasks: BackgroundTasks, db: DbSession = Depends(get_db),
          user: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    run, created = service.start_crawl(db, website_id, max_pages=body.max_pages, user_id=user.id)
    if created:
        tasks.add_task(service.execute_crawl, run.id)
    return _run(run)


@router.get("/{website_id}/crawls")
def crawls(website_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.get_website(db, website_id)
    return [_run(r) for r in service.runs(db, website_id)]


@router.get("/{website_id}/pages")
def pages(website_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.get_website(db, website_id)
    return [_page(p) for p in service.pages(db, website_id)]


@router.get("/{website_id}/pages/{page_id}")
def page(website_id: int, page_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    p, signals = service.page_detail(db, website_id, page_id)
    return {**_page(p), "signals": signals}


@router.get("/{website_id}/landing-pages")
def landing_pages(website_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.get_website(db, website_id)
    return service.landing_pages(db, website_id)


@router.post("/{website_id}/landing-pages/refresh", dependencies=[Depends(verify_origin)])
def refresh_landing(website_id: int, db: DbSession = Depends(get_db),
                    _: CurrentUser = Depends(require_permission(Permission.RECOMMEND))) -> dict:
    return {"mapped": service.refresh_landing_pages(db, website_id)}
