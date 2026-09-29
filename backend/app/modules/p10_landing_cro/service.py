"""P10 — landing-page checks for the URLs the account's ads point to (any domain the business owns), CRO findings and
website implementation briefs. Read-only towards Google Ads and the websites."""
import json
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlparse, urlunparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel.interface import list_websites
from app.modules.p05_ads_sync.interface import ads, keywords, list_accounts
from app.modules.p06_analytics.interface import tracking_health
from app.modules.p10_landing_cro import brief as briefs
from app.modules.p10_landing_cro import rules
from app.modules.p10_landing_cro.extract import extract
from app.modules.p10_landing_cro.fetch import fetch_pages
from app.modules.p10_landing_cro.models import CroFinding, ImplementationBrief, LandingPageCheck
from app.modules.p21_business_rules.interface import get_rules
from app.shared.errors import AppError, NotFoundError
from app.shared.feature_flags import is_enabled, require_enabled
from app.shared.logging import get_logger

MODULE_ID = "P10"
FETCH_FLAG = "crawler.enabled"      # declared by P03 (approved for the business's own sites); read-only here
AI_FLAG = "ai.live_calls.enabled"   # declared by P14; read-only here
MAX_URLS = 25
WINDOW_DAYS = 90
log = get_logger(MODULE_ID)


class AIFailed(AppError):
    status_code = 502
    code = "ai_failed"


def _utc(v: datetime | str | None) -> datetime | None:
    """SQLite drops tzinfo (and aggregates return strings); timestamps are stored in UTC, so label them as such."""
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    return v.replace(tzinfo=UTC) if v is not None and v.tzinfo is None else v


def account(db: DbSession, account_id: int):
    acc = next((a for a in list_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or not active", module_id=MODULE_ID)
    return acc


def norm(url: str) -> str:
    p = urlparse(url.strip())
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunparse(("https", p.netloc.lower().removeprefix("www."), path, "", "", ""))


def landing_contexts(db: DbSession, account_id: int) -> dict[str, dict]:
    """Normalised landing URL → the ads, ad groups, keywords and 90-day spend pointing to it (biggest spend first)."""
    d2 = date.today()
    d1 = d2 - timedelta(days=WINDOW_DAYS - 1)
    kw_by_group: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for k in keywords(db, account_id, d1, d2):
        if k.get("status") != "REMOVED":
            kw_by_group[(k["campaign_name"], k["ad_group_name"])].append(k)
    out: dict[str, dict] = {}
    for a in ads(db, account_id, d1, d2):
        if a.get("status") == "REMOVED" or not a.get("final_urls"):
            continue
        key = norm(a["final_urls"][0])
        c = out.setdefault(key, {"url": a["final_urls"][0], "ads": [], "ad_groups": [], "cost": 0.0, "clicks": 0,
                                 "conversions": 0.0, "_groups": set()})
        c["ads"].append({"key": a["key"], "status": a["status"], "campaign_name": a["campaign_name"],
                         "ad_group_name": a["ad_group_name"], "headlines": a["headlines"][:15]})
        c["cost"] += a["cost"]
        c["clicks"] += a["clicks"]
        c["conversions"] += a["conversions"]
        c["_groups"].add((a["campaign_name"], a["ad_group_name"]))
    for c in out.values():
        groups = sorted(c.pop("_groups"))
        c["ad_groups"] = [f"{cn} › {gn}" for cn, gn in groups]
        kws: dict[str, dict] = {}
        for g in groups:
            for k in kw_by_group.get(g, []):
                row = kws.setdefault(k["text"].lower(), {"text": k["text"], "clicks": 0, "conversions": 0.0})
                row["clicks"] += k["clicks"]
                row["conversions"] += k["conversions"]
        c["keywords"] = sorted(kws.values(), key=lambda k: -k["clicks"])[:60]
        c["cost"], c["conversions"] = round(c["cost"], 2), round(c["conversions"], 2)
    return dict(sorted(out.items(), key=lambda kv: (-kv[1]["cost"], -len(kv[1]["ads"]))))


def _tracking_by_host(db: DbSession, account_id: int) -> dict[str, list[str]]:
    d2 = date.today()
    d1 = d2 - timedelta(days=29)
    out = {}
    for w in list_websites(db):
        if w.ads_account_id != account_id:
            continue
        try:
            out[w.domain.lower().removeprefix("www.")] = [h["title"] for h in tracking_health(db, w.id, d1, d2) if h["severity"] == "critical"]
        except Exception:  # noqa: BLE001 — a caveat, never a blocker
            log.warning("tracking_health_failed", extra={"website_id": w.id})
    return out


def run_check(db: DbSession, account_id: int, *, by: str, fetcher=None) -> str:
    account(db, account_id)
    require_enabled(FETCH_FLAG, db, module_id=MODULE_ID)
    ctxs = dict(list(landing_contexts(db, account_id).items())[:MAX_URLS])
    if not ctxs:
        raise NotFoundError("No ads with landing pages found — sync the Google Ads account first", module_id=MODULE_ID)
    r = get_rules(db, account_id)
    tracking = _tracking_by_host(db, account_id)
    pages = (fetcher or fetch_pages)([c["url"] for c in ctxs.values()])
    run_key = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    for (key, ctx), page in zip(ctxs.items(), pages, strict=True):
        ok = bool(page.html) and page.status_code is not None and page.status_code < 400
        sig = extract(page.html).to_dict() if ok else None
        pd = {"url": page.url, "status_code": page.status_code, "final_url": page.final_url, "elapsed_ms": page.elapsed_ms,
              "error": page.error}
        found = rules.check(pd, sig, ctx, locations=r.locations, tracking_issues=tracking.get(urlparse(key).netloc))
        row = LandingPageCheck(account_id=account_id, run_key=run_key, url=page.url, final_url=page.final_url,
                               status_code=page.status_code, elapsed_ms=page.elapsed_ms, error=page.error,
                               signals=json.dumps(sig) if sig else None, context=json.dumps(ctx, default=str),
                               score=rules.score(found), checked_by=by)
        db.add(row)
        db.flush()
        for f in found:
            db.add(CroFinding(check_id=row.id, code=f.code, category=f.category, severity=f.severity, title=f.title,
                              detail=f.detail, recommendation=f.recommendation, evidence=json.dumps(f.evidence, default=str)))
    db.commit()
    log.info("landing_check_done", extra={"account_id": account_id, "pages": len(pages)})
    return run_key


def runs(db: DbSession, account_id: int) -> list[dict]:
    q = (select(LandingPageCheck.run_key, func.min(LandingPageCheck.checked_at), func.count(), func.avg(LandingPageCheck.score))
         .where(LandingPageCheck.account_id == account_id).group_by(LandingPageCheck.run_key)
         .order_by(LandingPageCheck.run_key.desc()).limit(20))
    return [{"run_key": k, "checked_at": _utc(t), "pages": n, "avg_score": round(s or 0)} for k, t, n, s in db.execute(q)]


def checks(db: DbSession, account_id: int, run_key: str | None = None) -> list[LandingPageCheck]:
    key = run_key or db.scalar(select(func.max(LandingPageCheck.run_key)).where(LandingPageCheck.account_id == account_id))
    if not key:
        return []
    return list(db.scalars(select(LandingPageCheck).where(LandingPageCheck.account_id == account_id, LandingPageCheck.run_key == key)
                           .order_by(LandingPageCheck.score, LandingPageCheck.id)))


def get_check(db: DbSession, check_id: int) -> LandingPageCheck:
    c = db.get(LandingPageCheck, check_id)
    if c is None:
        raise NotFoundError("Landing page check not found", module_id=MODULE_ID)
    return c


def findings(db: DbSession, check_id: int) -> list[dict]:
    order = {"critical": 0, "warning": 1, "info": 2}
    rows = db.scalars(select(CroFinding).where(CroFinding.check_id == check_id))
    return sorted([{"code": f.code, "category": f.category, "severity": f.severity, "title": f.title, "detail": f.detail,
                    "recommendation": f.recommendation, "evidence": json.loads(f.evidence)} for f in rows],
                  key=lambda f: (order[f["severity"]], rules.CATEGORIES.index(f["category"])))


def check_dict(db: DbSession, c: LandingPageCheck, *, full: bool = False) -> dict:
    ctx = json.loads(c.context)
    fs = findings(db, c.id)
    sig = json.loads(c.signals) if c.signals else None
    d = {"id": c.id, "run_key": c.run_key, "url": c.url, "final_url": c.final_url, "status_code": c.status_code,
         "elapsed_ms": c.elapsed_ms, "error": c.error, "score": c.score, "checked_at": _utc(c.checked_at), "checked_by": c.checked_by,
         "ads": len(ctx.get("ads", [])), "ad_groups": ctx.get("ad_groups", []), "cost": ctx.get("cost", 0),
         "clicks": ctx.get("clicks", 0), "conversions": ctx.get("conversions", 0),
         "counts": {s: sum(f["severity"] == s for f in fs) for s in ("critical", "warning", "info")},
         "findings": fs, "latest_brief_id": db.scalar(select(func.max(ImplementationBrief.id)).where(ImplementationBrief.check_id == c.id))}
    if full:
        d["context"] = ctx
        d["signals"] = {k: v for k, v in (sig or {}).items() if k != "text"} if sig else None
    return d


def ai_live(db: DbSession) -> bool:
    return is_enabled(AI_FLAG, db) and bool(briefs.P10Settings().anthropic_api_key)


def create_brief(db: DbSession, check_id: int, *, use_ai: bool, by: str) -> ImplementationBrief:
    c = get_check(db, check_id)
    r = get_rules(db, c.account_id)
    ctx, fs = json.loads(c.context), findings(db, c.id)
    sig = json.loads(c.signals) if c.signals else None
    mode, model, tokens = "template", None, None
    if use_ai and ai_live(db):
        try:
            b, tokens, model = briefs.write_with_claude(
                briefs.brief_input(c.url, c.score, fs, sig, ctx, r.locations, r.services), briefs.P10Settings())
            mode = "live"
        except briefs.BriefError as e:
            raise AIFailed(str(e), module_id=MODULE_ID) from e
    else:
        b = briefs.template_brief(c.url, fs, ctx, r.locations)
    row = ImplementationBrief(check_id=c.id, account_id=c.account_id, url=c.url, mode=mode, model=model,
                              content=b.model_dump_json(), output_tokens=tokens, created_by=by)
    db.add(row)
    db.commit()
    return row


def get_brief(db: DbSession, brief_id: int) -> ImplementationBrief:
    b = db.get(ImplementationBrief, brief_id)
    if b is None:
        raise NotFoundError("Brief not found", module_id=MODULE_ID)
    return b


def brief_dict(b: ImplementationBrief) -> dict:
    return {"id": b.id, "check_id": b.check_id, "url": b.url, "mode": b.mode, "model": b.model, "created_by": b.created_by,
            "created_at": _utc(b.created_at), "brief": json.loads(b.content)}


def brief_markdown(b: ImplementationBrief) -> str:
    return briefs.to_markdown(b.url, briefs.Brief.model_validate_json(b.content))


def latest_scores(db: DbSession, account_id: int) -> list[dict]:
    """For other modules (P14/P19): latest score + critical count per landing URL."""
    return [{"url": c.url, "score": c.score, "critical": sum(f["severity"] == "critical" for f in findings(db, c.id)),
             "checked_at": _utc(c.checked_at)} for c in checks(db, account_id)]
