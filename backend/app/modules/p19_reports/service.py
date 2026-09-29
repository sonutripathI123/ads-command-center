"""P19 — generate account/website reports, store the snapshot, export CSV / print-ready HTML (→ PDF via the browser)."""
import json
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel.interface import list_websites
from app.modules.p05_ads_sync.interface import campaigns, list_accounts, search_terms, summary
from app.modules.p06_analytics.interface import website_overview
from app.modules.p13_booking_funnel.interface import website_funnel
from app.modules.p14_recommendations.interface import open_recommendations
from app.modules.p16_approvals.interface import decisions
from app.modules.p18_monitoring.interface import open_alerts
from app.modules.p19_reports import builder, render
from app.modules.p19_reports.models import ReportRun
from app.shared.errors import NotFoundError, ValidationFailed

MODULE_ID = "P19"
NOTE = "Figures come from the last data sync — sync Google Ads and GA4 first for up-to-date numbers. Nothing in this report was changed in Google Ads."


def _utc(v):
    return v.replace(tzinfo=UTC) if v is not None and v.tzinfo is None else v


def _funnel(db: DbSession, w, d1: date, d2: date) -> dict:
    f = website_funnel(db, w.id, d1, d2)
    return {"website": w.name, "stages": f["stages"], "bottlenecks": f["bottlenecks"]}


def account_content(db: DbSession, account_id: int, d1: date, d2: date, p1: date, p2: date) -> tuple[str, dict]:
    acc = next((a for a in list_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or not active", module_id=MODULE_ID)
    k = builder.kpis(summary(db, account_id, d1, d2)["totals"], summary(db, account_id, p1, p2)["totals"])
    camps = [c for c in campaigns(db, account_id, d1, d2) if c["cost"] or c["clicks"]][:20]
    terms = search_terms(db, account_id, d1, d2, limit=15)
    sites = [w for w in list_websites(db) if w.ads_account_id == account_id]
    recs = [{k2: r[k2] for k2 in ("priority", "severity", "title", "status")} for r in open_recommendations(db, account_id)[:10]]
    content = {"headline": builder.headline(k), "kpis": k,
               "campaigns": [{x: c[x] for x in ("name", "status", "clicks", "cost", "conversions", "cost_per_conversion")} for c in camps],
               "search_terms": [{x: t[x] for x in ("search_term", "clicks", "cost", "conversions")} for t in terms],
               "funnels": [_funnel(db, w, d1, d2) for w in sites], "recommendations": recs,
               "approvals": decisions(db, account_id, d1, d2), "alerts": open_alerts(db, account_id), "notes": [NOTE]}
    return acc.descriptive_name or acc.customer_id, content


def website_content(db: DbSession, website_id: int, d1: date, d2: date) -> tuple[str, dict]:
    w = next((w for w in list_websites(db) if w.id == website_id), None)
    if w is None:
        raise NotFoundError("Website not found", module_id=MODULE_ID)
    ov = website_overview(db, w.id, d1, d2)
    t = ov["totals"]
    head = [f"{t['sessions']:,} sessions, {t['engaged_sessions']:,} engaged, {t['key_events']:g} key events (GA4).",
            f"{ov['organic_totals']['clicks']:,} organic clicks from {ov['organic_totals']['impressions']:,} impressions (Search Console).",
            f"{ov['bookings']['count']} bookings, AUD {ov['bookings']['revenue']:,.2f} revenue."]
    notes = [NOTE]
    if ov.get("ga4_first_day") and ov["ga4_first_day"] > d1:
        notes.insert(0, f"GA4 data starts on {ov['ga4_first_day']}; earlier days show no traffic.")
    content = {"headline": head, "ga4_channels": ov["channels"], "gsc_queries": ov["top_queries"][:15], "bookings": ov["bookings"],
               "issues": [h for h in ov["health"] if h["severity"] in ("critical", "warning")], "funnels": [_funnel(db, w, d1, d2)],
               "notes": notes}
    return w.name, content


def generate(db: DbSession, *, scope: str, scope_id: int, period: str, d1: date | None, d2: date | None, by: str,
             today: date | None = None) -> ReportRun:
    try:
        a, b, label = builder.period(period, today or date.today(), d1, d2)
    except ValueError as e:
        raise ValidationFailed(str(e), module_id=MODULE_ID) from e
    p1, p2 = builder.previous(a, b, period)
    if scope == "account":
        name, content = account_content(db, scope_id, a, b, p1, p2)
    elif scope == "website":
        name, content = website_content(db, scope_id, a, b)
    else:
        raise ValidationFailed("scope must be account or website", module_id=MODULE_ID)
    content["period_label"], content["previous"] = label, [str(p1), str(p2)]
    title = f"{period.capitalize()} {'Google Ads' if scope == 'account' else 'website'} report — {name}"
    r = ReportRun(scope=scope, scope_id=scope_id, period=period, date_from=a, date_to=b, title=title[:255],
                  content=json.dumps(content, default=str), created_by=by)
    db.add(r)
    db.commit()
    return r


def get(db: DbSession, report_id: int) -> ReportRun:
    r = db.get(ReportRun, report_id)
    if r is None:
        raise NotFoundError("Report not found", module_id=MODULE_ID)
    return r


def list_runs(db: DbSession, limit: int = 50) -> list[ReportRun]:
    return list(db.scalars(select(ReportRun).order_by(ReportRun.id.desc()).limit(limit)))


def run_dict(r: ReportRun, *, full: bool = True) -> dict:
    c = json.loads(r.content)
    d = {"id": r.id, "scope": r.scope, "scope_id": r.scope_id, "period": r.period, "date_from": r.date_from, "date_to": r.date_to,
         "title": r.title, "period_label": c.get("period_label", ""), "created_by": r.created_by, "created_at": _utc(r.created_at)}
    return d | {"content": c} if full else d


def csv_text(r: ReportRun) -> str:
    return render.to_csv(run_dict(r))


def html_text(r: ReportRun) -> str:
    return render.to_html(run_dict(r))


def scopes(db: DbSession) -> dict:
    return {"accounts": [{"id": a.id, "name": a.descriptive_name or a.customer_id} for a in list_accounts(db)],
            "websites": [{"id": w.id, "name": w.name} for w in list_websites(db)], "periods": list(builder.PERIODS),
            "generated_at": datetime.now(UTC)}
