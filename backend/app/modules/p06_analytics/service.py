"""P06 — GA4 / Search Console sync, conversion mapping, tracking health checks, booking import."""
import csv
import io
import json
import re
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel.interface import WebsiteRef, list_websites
from app.modules.p05_ads_sync.interface import summary as ads_summary
from app.modules.p06_analytics.adapters.google import GA4Client, GoogleDataError, SearchConsoleClient, ServiceAccount
from app.modules.p06_analytics.models import (
    AnalyticsDaily, AnalyticsSyncRun, Booking, ConversionEvent, ConversionMapping, SearchConsoleDaily,
)
from app.shared.db import session_scope
from app.shared.errors import NotFoundError, ValidationFailed
from app.shared.logging import get_logger

MODULE_ID = "P06"
ROLES = ("lead", "booking", "micro", "ignore")
STALE = timedelta(minutes=30)
log = get_logger(MODULE_ID)


class P06Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    google_service_account_file: str | None = None


def website(db: DbSession, website_id: int) -> WebsiteRef:
    w = next((w for w in list_websites(db) if w.id == website_id), None)
    if w is None:
        raise NotFoundError("Website not found", module_id=MODULE_ID)
    return w


# ---- sync -------------------------------------------------------------------------------

def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _gdate(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))  # GA4 returns YYYYMMDD


def start_sync(db: DbSession, w: WebsiteRef, days: int) -> tuple[AnalyticsSyncRun, bool]:
    if not w.ga4_property_id and not w.gsc_site_url:
        raise ValidationFailed("Add a GA4 property ID or Search Console property to this website first (Websites page)",
                               module_id=MODULE_ID)
    cutoff = datetime.now(UTC) - STALE
    for r in db.scalars(select(AnalyticsSyncRun).where(AnalyticsSyncRun.website_id == w.id, AnalyticsSyncRun.status == "running")):
        started = r.started_at if r.started_at.tzinfo else r.started_at.replace(tzinfo=UTC)
        if started >= cutoff:
            return r, False
        r.status, r.errors = "failed", json.dumps({"interrupted": "did not finish"})
    d2 = date.today() - timedelta(days=1)
    run = AnalyticsSyncRun(website_id=w.id, date_from=d2 - timedelta(days=days - 1), date_to=d2)
    db.add(run)
    db.commit()
    return run, True


def _replace(db: DbSession, model, website_id: int, d1: date, d2: date, rows: list) -> int:
    db.execute(delete(model).where(model.website_id == website_id, model.date >= d1, model.date <= d2))
    db.add_all(rows)
    return len(rows)


def execute_sync(run_id: int, http_factory: Callable[[], httpx.Client] = lambda: httpx.Client(timeout=60)) -> None:
    with session_scope() as db, http_factory() as http:
        run = db.get(AnalyticsSyncRun, run_id)
        w = website(db, run.website_id)
        d1, d2 = run.date_from, run.date_to
        counts, errors = {}, {}
        try:
            path = P06Settings().google_service_account_file
            if not path:
                raise GoogleDataError("GOOGLE_SERVICE_ACCOUNT_FILE is not set in backend/.env")
            sa = ServiceAccount(path, http)
        except GoogleDataError as e:
            errors["auth"], sa = e.message, None
        if sa and w.ga4_property_id:
            ga = GA4Client(sa)
            try:
                rows = ga.report(w.ga4_property_id, start=d1.isoformat(), end=d2.isoformat(),
                                 dimensions=["date", "sessionDefaultChannelGroup"],
                                 metrics=["sessions", "engagedSessions", "totalUsers", "keyEvents"])
                counts["ga4_traffic"] = _replace(db, AnalyticsDaily, w.id, d1, d2, [AnalyticsDaily(
                    website_id=w.id, date=_gdate(r["date"]), channel=r["sessionDefaultChannelGroup"][:64],
                    sessions=int(_num(r["sessions"])), engaged_sessions=int(_num(r["engagedSessions"])),
                    users=int(_num(r["totalUsers"])), key_events=_num(r["keyEvents"])) for r in rows])
                db.commit()
            except GoogleDataError as e:
                db.rollback()
                errors["ga4_traffic"] = e.message
            try:
                rows = ga.report(w.ga4_property_id, start=d1.isoformat(), end=d2.isoformat(),
                                 dimensions=["date", "eventName"], metrics=["eventCount", "keyEvents"])
                counts["ga4_events"] = _replace(db, ConversionEvent, w.id, d1, d2, [ConversionEvent(
                    website_id=w.id, date=_gdate(r["date"]), event_name=r["eventName"][:128],
                    event_count=int(_num(r["eventCount"])), key_events=_num(r["keyEvents"])) for r in rows])
                db.commit()
            except GoogleDataError as e:
                db.rollback()
                errors["ga4_events"] = e.message
        if sa and w.gsc_site_url:
            try:
                rows = SearchConsoleClient(sa).query(w.gsc_site_url, start=d1.isoformat(), end=d2.isoformat(),
                                                     dimensions=["date", "query"])
                counts["search_console"] = _replace(db, SearchConsoleDaily, w.id, d1, d2, [SearchConsoleDaily(
                    website_id=w.id, date=date.fromisoformat(r["date"]), query=r["query"][:512], clicks=int(r["clicks"]),
                    impressions=int(r["impressions"]), position=float(r["position"])) for r in rows])
                db.commit()
            except GoogleDataError as e:
                db.rollback()
                errors["search_console"] = e.message
        run = db.get(AnalyticsSyncRun, run_id)
        run.counts, run.errors = json.dumps(counts), json.dumps(errors)
        run.status = "success" if not errors else ("partial" if counts else "failed")
        run.finished_at = datetime.now(UTC)
        db.commit()
        log.info("analytics_sync_finished", extra={"run_id": run_id, "status": run.status, "counts": counts})


def runs(db: DbSession, website_id: int, limit: int = 10) -> list[AnalyticsSyncRun]:
    return list(db.scalars(select(AnalyticsSyncRun).where(AnalyticsSyncRun.website_id == website_id)
                           .order_by(AnalyticsSyncRun.id.desc()).limit(limit)))


# ---- conversion mapping -------------------------------------------------------------------

_SUGGEST = [
    (re.compile(r"purchase|booking_complete|book_complete|booking_confirmed|payment", re.I), "booking"),
    (re.compile(r"form_submit|generate_lead|submit_lead|lead|quote_request|enquir|inquir|contact_submit|click_to_call|phone_click|call", re.I), "lead"),
    (re.compile(r"form_start|begin_checkout|add_to_cart|click|scroll|file_download|video", re.I), "micro"),
    (re.compile(r"^(page_view|session_start|first_visit|user_engagement)$", re.I), "ignore"),
]


def suggest_role(event_name: str) -> str:
    for rx, role in _SUGGEST:
        if rx.search(event_name):
            return role
    return "micro"


def set_mapping(db: DbSession, website_id: int, event_name: str, role: str, email: str) -> ConversionMapping:
    if role not in ROLES:
        raise ValidationFailed(f"role must be one of {ROLES}", module_id=MODULE_ID)
    m = db.scalar(select(ConversionMapping).where(ConversionMapping.website_id == website_id,
                                                  ConversionMapping.event_name == event_name))
    m = m or ConversionMapping(website_id=website_id, event_name=event_name[:128], role=role)
    m.role, m.updated_by = role, email
    db.add(m)
    db.commit()
    return m


# ---- overview + health ---------------------------------------------------------------------

def overview(db: DbSession, w: WebsiteRef, d1: date, d2: date) -> dict:
    traffic = defaultdict(lambda: {"sessions": 0, "engaged_sessions": 0, "users": 0, "key_events": 0.0})
    daily: dict[date, int] = defaultdict(int)
    first_day = None
    for r in db.scalars(select(AnalyticsDaily).where(AnalyticsDaily.website_id == w.id, AnalyticsDaily.date >= d1,
                                                     AnalyticsDaily.date <= d2)):
        t = traffic[r.channel]
        t["sessions"] += r.sessions
        t["engaged_sessions"] += r.engaged_sessions
        t["users"] += r.users
        t["key_events"] += r.key_events
        daily[r.date] += r.sessions
        if r.sessions and (first_day is None or r.date < first_day):
            first_day = r.date
    mappings = {m.event_name: m.role for m in db.scalars(select(ConversionMapping).where(ConversionMapping.website_id == w.id))}
    events = [{"event_name": n, "event_count": int(c or 0), "key_events": float(k or 0), "role": mappings.get(n),
               "suggested_role": suggest_role(n)}
              for n, c, k in db.execute(select(ConversionEvent.event_name, func.sum(ConversionEvent.event_count),
                                               func.sum(ConversionEvent.key_events))
                                        .where(ConversionEvent.website_id == w.id, ConversionEvent.date >= d1,
                                               ConversionEvent.date <= d2).group_by(ConversionEvent.event_name))]
    events.sort(key=lambda e: -e["event_count"])
    queries = [{"query": q, "clicks": int(c or 0), "impressions": int(i or 0), "position": round(float(p or 0), 1)}
               for q, c, i, p in db.execute(
                   select(SearchConsoleDaily.query, func.sum(SearchConsoleDaily.clicks), func.sum(SearchConsoleDaily.impressions),
                          func.avg(SearchConsoleDaily.position))
                   .where(SearchConsoleDaily.website_id == w.id, SearchConsoleDaily.date >= d1, SearchConsoleDaily.date <= d2)
                   .group_by(SearchConsoleDaily.query))]
    queries.sort(key=lambda q: (-q["clicks"], -q["impressions"]))
    bk = bookings_summary(db, d1, d2, w.id)
    channels = sorted(({"channel": k, **v} for k, v in traffic.items()), key=lambda r: -r["sessions"])
    day, series = d1, []
    while day <= d2:
        series.append({"date": day.isoformat(), "sessions": daily.get(day, 0)})
        day += timedelta(days=1)
    ov = {"date_from": d1, "date_to": d2, "ga4_first_day": first_day, "channels": channels, "daily": series,
          "totals": {k: sum(c[k] for c in channels) for k in ("sessions", "engaged_sessions", "users", "key_events")},
          "events": events, "top_queries": queries[:100], "organic_totals": {
              "clicks": sum(q["clicks"] for q in queries), "impressions": sum(q["impressions"] for q in queries)},
          "bookings": bk}
    ov["health"] = health(db, w, ov)
    return ov


LEAD_NAMES = re.compile(r"form_submit|generate_lead|submit|lead|enquir|inquir|quote|purchase|booking|book_", re.I)


def health(db: DbSession, w: WebsiteRef, ov: dict) -> list[dict]:
    out: list[dict] = []

    def add(severity: str, code: str, title: str, detail: str):
        out.append({"severity": severity, "code": code, "title": title, "detail": detail})

    t, events = ov["totals"], {e["event_name"]: e for e in ov["events"]}
    if not w.ga4_property_id:
        add("warning", "no_ga4", "GA4 not linked", "Add the GA4 property ID on the Websites page to measure visits and leads.")
    else:
        if not t["sessions"]:
            add("warning", "no_ga4_data", "No GA4 data yet", "Run a sync. If it stays empty, check the service account has Viewer access to the property.")
        first = ov["ga4_first_day"]
        if first and first > ov["date_from"] + timedelta(days=6):
            add("info", "ga4_started_late", f"GA4 data only starts on {first.isoformat()}",
                "Anything before this date has no analytics — compare periods after it only.")
        if t["sessions"] >= 50 and t["key_events"] == 0:
            add("critical", "no_key_events", "GA4 records no conversions (key events)",
                f"{t['sessions']} sessions but 0 key events. Mark your enquiry/booking event as a key event in GA4 "
                "(Admin → Events → Mark as key event), otherwise nobody can see which traffic produces leads.")
        if "form_start" in events and not any(LEAD_NAMES.search(n) and n != "form_start" for n in events):
            add("critical", "form_submit_missing", "Form starts are tracked, but not form submissions",
                f"{events['form_start']['event_count']} form_start events and no submit/lead event. Add a "
                "'generate_lead' (or form_submit) event on the thank-you step of the booking/quote form.")
        mapped = [n for n, e in events.items() if e["role"] in ("lead", "booking")]
        if events and not mapped:
            add("warning", "no_mapping", "No GA4 event is marked as a lead or booking here",
                "Use the 'Means' column below so reports can count leads.")
        paid = next((c["sessions"] for c in ov["channels"] if c["channel"] == "Paid Search"), 0)
        if w.ads_account_id and first:
            ads = ads_summary(db, w.ads_account_id, max(first, ov["date_from"]), ov["date_to"])["totals"]
            if ads["clicks"] >= 30:
                ratio = paid / ads["clicks"]
                if ratio < 0.6:
                    add("warning", "paid_sessions_low", "Far fewer GA4 paid sessions than Google Ads clicks",
                        f"{ads['clicks']} ad clicks vs {paid} GA4 Paid Search sessions ({ratio:.0%}) since {first}. Check the GA4 tag "
                        "on every landing page, auto-tagging, consent banner, and ads pointing to another domain.")
                if ads["conversions"] > 0 and t["key_events"] == 0:
                    add("warning", "ads_vs_ga4_conversions", "Google Ads counts conversions that GA4 doesn't",
                        f"Google Ads: {ads['conversions']:g} conversions; GA4: 0 key events. Check which conversion "
                        "actions Google Ads uses (Tools → Conversions) — they may be page views or calls, not real leads.")
    if not w.gsc_site_url:
        add("info", "no_gsc", "Search Console not linked", "Add the Search Console property to see organic Google searches.")
    if not ov["bookings"]["count"]:
        add("info", "no_bookings", "No bookings imported",
            "Import bookings (CSV now, Driver App connection next) to see real revenue per channel, not just clicks.")
    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(out, key=lambda f: order[f["severity"]])


# ---- bookings (confirmed) -----------------------------------------------------------------------

_ALIASES = {
    "booking_id": ("booking_id", "id", "booking", "booking_ref", "reference", "ref", "job_id"),
    "booked_on": ("booked_on", "booking_date", "created_at", "created", "date_booked", "date"),
    "amount": ("amount", "total", "price", "fare", "revenue", "value"),
    "service_date": ("service_date", "pickup_date", "trip_date", "job_date"),
    "status": ("status", "booking_status"),
    "service_type": ("service_type", "service", "type"),
    "website": ("website", "site", "domain", "brand"),
    "channel": ("channel", "source_channel", "how_heard", "lead_source"),
    "utm_source": ("utm_source",), "utm_medium": ("utm_medium",), "utm_campaign": ("utm_campaign",), "gclid": ("gclid",),
}


def _parse_date(s: str) -> date | None:
    """Accepts 2026-09-01, 2026-09-01T10:30:00, 1/9/2026, 01-09-2026, 1/9/26 (Australian day-first)."""
    part = (s or "").strip().split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y"):  # %y first: "%Y" would read "26" as year 26
        try:
            return datetime.strptime(part, fmt).date()
        except ValueError:
            continue
    return None


def import_bookings(db: DbSession, text: str, *, default_website_id: int | None) -> dict:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames:
        raise ValidationFailed("CSV has no header row", module_id=MODULE_ID)
    header = {h.strip().lower().replace(" ", "_"): h for h in reader.fieldnames}
    col = {k: next((header[a] for a in al if a in header), None) for k, al in _ALIASES.items()}
    missing = [k for k in ("booking_id", "booked_on", "amount") if not col[k]]
    if missing:
        raise ValidationFailed(f"CSV is missing required column(s): {', '.join(missing)}", module_id=MODULE_ID,
                               details={"accepted": {k: list(v) for k, v in _ALIASES.items()}})
    sites = {w.domain: w.id for w in list_websites(db)}
    created = updated = 0
    errors: list[str] = []
    existing = {b.external_id: b for b in db.scalars(select(Booking).where(Booking.source_system == "csv"))}
    for n, row in enumerate(reader, start=2):
        get = lambda k: (row.get(col[k]) or "").strip() if col[k] else ""  # noqa: E731
        ext, booked = get("booking_id"), _parse_date(get("booked_on"))
        amount = re.sub(r"[^\d.\-]", "", get("amount"))
        if not ext or booked is None:
            errors.append(f"line {n}: missing booking id or unreadable date")
            continue
        site = get("website").lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").split("/")[0]
        b = existing.get(ext)
        if b is None:
            b = Booking(source_system="csv", external_id=ext[:128])
            existing[ext] = b
            created += 1
        else:
            updated += 1
        b.booked_on, b.service_date = booked, _parse_date(get("service_date"))
        b.amount = float(amount) if amount not in ("", "-", ".") else 0.0
        b.status, b.service_type = (get("status") or "confirmed")[:32].lower(), get("service_type")[:64]
        b.website_id = sites.get(site, default_website_id)
        b.channel, b.gclid = get("channel")[:64], get("gclid")[:255]
        b.utm_source, b.utm_medium, b.utm_campaign = get("utm_source")[:128], get("utm_medium")[:128], get("utm_campaign")[:255]
        db.add(b)
    db.commit()
    log.info("bookings_imported", extra={"rows_created": created, "rows_updated": updated, "rows_skipped": len(errors)})
    return {"created": created, "updated": updated, "skipped": len(errors), "errors": errors[:20],
            "ignored_columns": sorted(set(header) - {a for al in _ALIASES.values() for a in al})}


CANCELLED = ("cancelled", "canceled", "void", "refunded")


def is_google_ads(b: Booking) -> bool:
    return bool(b.gclid) or (b.utm_source.lower() == "google" and b.utm_medium.lower() in ("cpc", "ppc", "paid")) \
        or "google ads" in b.channel.lower() or "adwords" in b.channel.lower()


def bookings_summary(db: DbSession, d1: date, d2: date, website_id: int | None = None) -> dict:
    q = select(Booking).where(Booking.booked_on >= d1, Booking.booked_on <= d2)
    if website_id is not None:
        q = q.where(Booking.website_id == website_id)
    rows = [b for b in db.scalars(q) if b.status not in CANCELLED]
    by_channel: dict[str, dict] = defaultdict(lambda: {"count": 0, "revenue": 0.0})
    for b in rows:
        key = "Google Ads" if is_google_ads(b) else (b.channel or b.utm_source or "Unknown")
        by_channel[key]["count"] += 1
        by_channel[key]["revenue"] = round(by_channel[key]["revenue"] + b.amount, 2)
    return {"count": len(rows), "revenue": round(sum(b.amount for b in rows), 2),
            "google_ads": by_channel.get("Google Ads", {"count": 0, "revenue": 0.0}),
            "by_channel": sorted(({"channel": k, **v} for k, v in by_channel.items()), key=lambda r: -r["revenue"])}
