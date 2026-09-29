"""P13 — funnel per website (its GA4 + bookings) with its linked Google Ads account, compared with the previous period.
Campaign figures are those reported by Google Ads; booking-level revenue attribution by campaign needs per-booking rows
from P06 (not in its interface yet — see MODULE.md)."""
from datetime import date, timedelta

from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel.interface import list_websites
from app.modules.p05_ads_sync.interface import campaigns, list_accounts, summary
from app.modules.p06_analytics.interface import bookings_summary, website_overview
from app.modules.p13_booking_funnel import funnel
from app.shared.errors import NotFoundError, ValidationFailed

MODULE_ID = "P13"
EVER = date(2000, 1, 1)


def website(db: DbSession, website_id: int):
    w = next((w for w in list_websites(db) if w.id == website_id), None)
    if w is None:
        raise NotFoundError("Website not found", module_id=MODULE_ID)
    return w


def _period(d1: date | None, d2: date | None) -> tuple[date, date, date, date]:
    d2 = d2 or date.today()
    d1 = d1 or d2 - timedelta(days=29)
    if d1 > d2 or (d2 - d1).days > 730:
        raise ValidationFailed("Pick a period of up to 2 years (from ≤ to)", module_id=MODULE_ID)
    n = (d2 - d1).days + 1
    return d1, d2, d1 - timedelta(days=n), d1 - timedelta(days=1)


def _inputs(db: DbSession, w, account_id: int | None, d1: date, d2: date, has_bookings: bool):
    ads = summary(db, account_id, d1, d2)["totals"] if account_id else None
    ov = website_overview(db, w.id, d1, d2)
    ga = funnel.ga4_counts(ov)
    return ads, ga, (ov["bookings"] if has_bookings else None), ov


def website_funnel(db: DbSession, website_id: int, d1: date | None = None, d2: date | None = None) -> dict:
    w = website(db, website_id)
    d1, d2, p1, p2 = _period(d1, d2)
    acc = w.ads_account_id if any(a.id == w.ads_account_id for a in list_accounts(db)) else None
    has_bookings = bookings_summary(db, EVER, date.today(), w.id)["count"] > 0
    ads, ga, bk, ov = _inputs(db, w, acc, d1, d2, has_bookings)
    pads, pga, pbk, _ = _inputs(db, w, acc, p1, p2, has_bookings)
    first = ov.get("ga4_first_day")
    partial = str(first) if first and first > d1 else None
    prev = {s.key: s.value for s in funnel.build(pads, pga, pbk)}
    stages = funnel.build(ads, ga, bk, prev=prev, ga4_partial=bool(partial))
    camps = []
    if acc:
        for c in campaigns(db, acc, d1, d2):
            if c["cost"] or c["clicks"]:
                camps.append({k: c[k] for k in ("google_id", "name", "status", "impressions", "clicks", "cost", "conversions",
                                                  "conversions_value", "cost_per_conversion", "conv_rate")}
                             | {"roas_reported": round(c["conversions_value"] / c["cost"], 2) if c["cost"] else None})
    quality = []
    if bk:
        for ch in bk["by_channel"]:
            quality.append(ch | {"avg_value": round(ch["revenue"] / ch["count"], 2) if ch["count"] else None})
    return {"website": {"id": w.id, "name": w.name, "domain": w.domain, "ads_account_id": acc},
            "period": {"from": d1, "to": d2, "previous_from": p1, "previous_to": p2},
            "stages": funnel.to_dicts(stages), "bottlenecks": funnel.to_dicts(funnel.bottlenecks(stages, ads, ga, bk, ga4_from=partial)),
            "ads_reported": {k: ads[k] for k in ("cost", "conversions", "conversions_value", "cost_per_conversion")} if ads else None,
            "ga4": {"lead_events": ga.get("lead_events", []), "sessions": ga.get("sessions"), "paid_sessions": ga.get("paid_sessions"),
                    "first_day": ov.get("ga4_first_day")},
            "campaigns": sorted(camps, key=lambda c: -c["cost"]), "booking_quality": quality,
            "bookings_imported": has_bookings}


def websites(db: DbSession) -> list[dict]:
    return [{"id": w.id, "name": w.name, "domain": w.domain, "ads_account_id": w.ads_account_id} for w in list_websites(db)]
