"""P03 — websites, crawls, pages, landing-page mappings."""
import json
import re
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlparse

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel import crawler
from app.modules.p03_website_intel.extract import normalise_url, page_issues, same_site
from app.modules.p03_website_intel.models import CrawlRun, LandingPageMapping, Page, PageSignal, Website
from app.modules.p05_ads_sync.interface import ads as ads_rows
from app.modules.p05_ads_sync.interface import list_accounts
from app.modules.p21_business_rules.interface import get_rules
from app.shared.db import session_scope
from app.shared.errors import NotFoundError, ValidationFailed
from app.shared.feature_flags import require_enabled
from app.shared.logging import get_logger

MODULE_ID = "P03"
CRAWL_FLAG = "crawler.enabled"
STALE = timedelta(minutes=30)
log = get_logger(MODULE_ID)
EDITABLE = ("name", "primary_service", "location", "time_zone", "ads_account_id", "ga4_property_id", "gsc_site_url",
            "notes", "status")


def parse_domain(raw: str) -> tuple[str, str]:
    """'corporatecarsmelbourne.com.au/' → ('corporatecarsmelbourne.com.au', 'https://corporatecarsmelbourne.com.au')."""
    raw = raw.strip()
    if not raw:
        raise ValidationFailed("Domain is required", module_id=MODULE_ID)
    p = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (p.hostname or "").lower()
    if not re.fullmatch(r"(?=.{4,253}$)([a-z0-9-]+\.)+[a-z]{2,}", host):
        raise ValidationFailed(f"'{raw}' is not a valid domain", module_id=MODULE_ID)
    return host.removeprefix("www."), f"{p.scheme if p.scheme in ('http', 'https') else 'https'}://{host}"


def _validate_links(db: DbSession, fields: dict) -> None:
    acc = fields.get("ads_account_id")
    if acc is not None and not any(a.id == acc for a in list_accounts(db)):
        raise ValidationFailed("Unknown or inactive Google Ads account", module_id=MODULE_ID)
    ga4 = fields.get("ga4_property_id")
    if ga4 and not str(ga4).isdigit():
        raise ValidationFailed("GA4 property ID must be digits only (Admin → Property details)", module_id=MODULE_ID)
    if fields.get("status") not in (None, "active", "archived"):
        raise ValidationFailed("status must be active or archived", module_id=MODULE_ID)


def list_websites(db: DbSession, include_archived: bool = False) -> list[Website]:
    q = select(Website).order_by(Website.name)
    if not include_archived:
        q = q.where(Website.status == "active")
    return list(db.scalars(q))


def get_website(db: DbSession, website_id: int) -> Website:
    w = db.get(Website, website_id)
    if w is None:
        raise NotFoundError("Website not found", module_id=MODULE_ID)
    return w


def create_website(db: DbSession, *, domain: str, **fields) -> Website:
    host, base = parse_domain(domain)
    if db.scalar(select(Website).where(Website.domain == host)):
        raise ValidationFailed(f"{host} is already added", module_id=MODULE_ID)
    _validate_links(db, fields)
    w = Website(domain=host, base_url=base, **{k: v for k, v in fields.items() if k in EDITABLE and v is not None})
    db.add(w)
    db.commit()
    log.info("website_created", extra={"website_id": w.id, "domain": host})
    return w


def update_website(db: DbSession, website_id: int, fields: dict) -> Website:
    w = get_website(db, website_id)
    _validate_links(db, fields)
    for k, v in fields.items():
        if k in EDITABLE:
            setattr(w, k, v)
    db.commit()
    return w


# ---- crawling ------------------------------------------------------------------------

def _phrase_hits(text: str, phrases: list[str]) -> list[str]:
    return [p for p in phrases if re.search(r"(?<![\w])" + re.escape(p) + r"(?![\w])", text)]


def _expire_stale(db: DbSession) -> None:
    cutoff = datetime.now(UTC) - STALE
    for r in db.scalars(select(CrawlRun).where(CrawlRun.status == "running")):
        started = r.started_at if r.started_at.tzinfo else r.started_at.replace(tzinfo=UTC)
        if started < cutoff:
            r.status, r.finished_at, r.errors = "failed", datetime.now(UTC), json.dumps(["interrupted"])
    db.commit()


def start_crawl(db: DbSession, website_id: int, *, max_pages: int, user_id: int | None) -> tuple[CrawlRun, bool]:
    """→ (run, created). An already-running crawl for the site is returned instead of starting another."""
    require_enabled(CRAWL_FLAG, db, module_id=MODULE_ID)
    w = get_website(db, website_id)
    _expire_stale(db)
    running = db.scalars(select(CrawlRun).where(CrawlRun.website_id == w.id, CrawlRun.status == "running")).first()
    if running:
        return running, False
    run = CrawlRun(website_id=w.id, max_pages=max_pages, triggered_by_user_id=user_id)
    db.add(run)
    db.commit()
    return run, True


def execute_crawl(run_id: int, http_factory: Callable[[], httpx.Client] | None = None, delay: float = 0.5,
                  sleep=None) -> None:
    with session_scope() as db:
        run = db.get(CrawlRun, run_id)
        w = db.get(Website, run.website_id)
        try:
            kwargs = {"sleep": sleep} if sleep else {}
            res = crawler.crawl(w.base_url, max_pages=run.max_pages, delay=delay, http_factory=http_factory, **kwargs)
        except Exception as e:  # noqa: BLE001 — recorded on the run
            run.status, run.finished_at, run.errors = "failed", datetime.now(UTC), json.dumps([str(e)[:300]])
            db.commit()
            return
        rules = get_rules(db, w.ads_account_id)
        now = datetime.now(UTC)
        existing = {p.url: p for p in db.scalars(select(Page).where(Page.website_id == w.id))}
        for f in res.pages:
            url = normalise_url(f.url)
            page = existing.get(url) or Page(website_id=w.id, url=url)
            page.status_code, page.final_url, page.response_ms = f.status, f.final_url, f.response_ms
            s = f.signals
            if s is not None:
                hay = " ".join([s.title, " ".join(s.h1), " ".join(s.h2), f.text]).lower()
                services, locations = _phrase_hits(hay, rules.services), _phrase_hits(hay, rules.locations)
                page.title, page.meta_description, page.h1 = s.title[:1000], s.meta_description[:2000], " | ".join(s.h1)[:1000]
                page.word_count, page.cta_count = s.word_count, len(s.ctas)
                page.has_form, page.has_phone = bool(s.forms), bool(s.phones or s.tel_links)
                page.services, page.locations = json.dumps(services[:20]), json.dumps(locations[:20])
                page.issues = json.dumps(page_issues(s, f.status, f.response_ms, services))
            else:
                page.issues = json.dumps(["http_error"] if (f.status or 500) >= 400 or f.status is None else [])
            page.last_crawl_run_id, page.last_crawled_at = run.id, now
            db.add(page)
            db.flush()
            if s is not None:
                db.add(PageSignal(page_id=page.id, crawl_run_id=run.id, signals=s.to_json()))
        run.pages_found, run.pages_crawled, run.source = res.discovered, len(res.pages), res.source
        run.errors = json.dumps(res.errors)
        ok = [f for f in res.pages if f.signals is not None and (f.status or 0) < 400]
        run.status = "failed" if not ok else ("partial" if res.errors else "success")
        run.finished_at = datetime.now(UTC)
        db.commit()
        try:
            refresh_landing_pages(db, w.id)
        except Exception as e:  # noqa: BLE001 — mapping is best-effort; crawl already stored
            log.warning("landing_map_failed", extra={"website_id": w.id, "error": str(e)[:200]})
        log.info("crawl_finished", extra={"run_id": run.id, "status": run.status, "pages": len(res.pages)})


def runs(db: DbSession, website_id: int, limit: int = 10) -> list[CrawlRun]:
    _expire_stale(db)
    return list(db.scalars(select(CrawlRun).where(CrawlRun.website_id == website_id)
                           .order_by(CrawlRun.id.desc()).limit(limit)))


def pages(db: DbSession, website_id: int) -> list[Page]:
    return list(db.scalars(select(Page).where(Page.website_id == website_id).order_by(Page.url)))


def page_detail(db: DbSession, website_id: int, page_id: int) -> tuple[Page, dict | None]:
    p = db.get(Page, page_id)
    if p is None or p.website_id != website_id:
        raise NotFoundError("Page not found", module_id=MODULE_ID)
    sig = db.scalars(select(PageSignal).where(PageSignal.page_id == p.id).order_by(PageSignal.id.desc()).limit(1)).first()
    return p, json.loads(sig.signals) if sig else None


# ---- landing pages ---------------------------------------------------------------------

def refresh_landing_pages(db: DbSession, website_id: int) -> int:
    """Map the linked Google Ads account's ad final URLs to crawled pages."""
    w = get_website(db, website_id)
    db.execute(delete(LandingPageMapping).where(LandingPageMapping.website_id == w.id))
    if w.ads_account_id is None:
        db.commit()
        return 0
    by_url = {p.url: p for p in pages(db, w.id)}
    today = date.today()
    n = 0
    for ad in ads_rows(db, w.ads_account_id, today - timedelta(days=89), today):
        for final in dict.fromkeys(ad["final_urls"]):
            url = normalise_url(final)
            page = by_url.get(url)
            if not same_site(urlparse(url).netloc, w.domain):
                status = "other_domain"
            elif page is None:
                status = "not_crawled"
            elif page.status_code is None or page.status_code >= 400:
                status = "broken"
            else:
                status = "ok"
            db.add(LandingPageMapping(website_id=w.id, ad_key=ad["key"], campaign_name=ad["campaign_name"],
                                      ad_group_name=ad["ad_group_name"], final_url=final[:1024],
                                      page_id=page.id if page else None, status=status))
            n += 1
    db.commit()
    return n


def landing_pages(db: DbSession, website_id: int) -> list[dict]:
    by_id = {p.id: p for p in pages(db, website_id)}
    out: dict[str, dict] = {}
    for m in db.scalars(select(LandingPageMapping).where(LandingPageMapping.website_id == website_id)):
        row = out.setdefault(m.final_url, {"final_url": m.final_url, "status": m.status, "page_id": m.page_id,
                                           "title": by_id[m.page_id].title if m.page_id in by_id else None,
                                           "issues": json.loads(by_id[m.page_id].issues) if m.page_id in by_id else [],
                                           "ads": 0, "ad_groups": set()})
        row["ads"] += 1
        row["ad_groups"].add(f"{m.campaign_name} › {m.ad_group_name}")
    for r in out.values():
        r["ad_groups"] = sorted(r["ad_groups"])
    order = {"broken": 0, "not_crawled": 1, "other_domain": 2, "ok": 3}
    return sorted(out.values(), key=lambda r: (order.get(r["status"], 9), -r["ads"]))
