"""P13 — pure Click → Visit → Lead → Booking → Revenue model with bottleneck detection.
Every stage says where its number comes from and whether it is measured at all; estimates are labelled."""
from dataclasses import asdict, dataclass

PAID_CHANNELS = ("Paid Search", "Cross-network")
# Rough benchmarks for Australian chauffeur search campaigns — used only to flag, never as targets.
BENCH = {"ctr": 0.03, "visit_rate": 0.6, "lead_rate": 0.03, "booking_rate": 0.15}


@dataclass
class Stage:
    key: str
    label: str
    value: float | None          # None = not measured
    source: str
    estimated: bool = False
    rate: float | None = None     # from the previous measured stage
    cost_per: float | None = None
    previous: float | None = None
    change: float | None = None


@dataclass
class Bottleneck:
    code: str
    severity: str                 # critical | warning | info
    stage: str
    title: str
    detail: str
    action: str
    link: str | None = None


def _div(a, b):
    return round(a / b, 4) if a is not None and b else None


def ga4_counts(ov: dict | None) -> dict:
    """From a P06 website_overview: paid/total sessions and lead/booking events (mapped role, else suggested role)."""
    if not ov:
        return {"measured": False}
    sessions = ov["totals"]["sessions"]
    paid = sum(c["sessions"] for c in ov["channels"] if c["channel"] in PAID_CHANNELS)
    role = lambda e: e["role"] or e["suggested_role"]  # noqa: E731
    leads = sum(e["event_count"] for e in ov["events"] if role(e) == "lead")
    bookings = sum(e["event_count"] for e in ov["events"] if role(e) == "booking")
    lead_events = [e["event_name"] for e in ov["events"] if role(e) == "lead"]
    return {"measured": bool(sessions), "sessions": sessions, "paid_sessions": paid, "leads": leads, "booking_events": bookings,
            "lead_events": lead_events, "unmapped": any(e["role"] is None for e in ov["events"] if e["suggested_role"] in ("lead", "booking"))}


def build(ads: dict | None, ga: dict, bk: dict | None, *, prev: dict | None = None, ga4_partial: bool = False) -> list[Stage]:
    """ads: P05 totals (or None if no linked account); ga: ga4_counts(); bk: P06 bookings_summary (None if nothing imported)."""
    share = _div(ga.get("paid_sessions"), ga.get("sessions")) if ga.get("measured") else None
    if not ga.get("measured") or not ga.get("lead_events"):
        est_leads = None  # no lead event → not measured (not zero)
    else:
        est_leads = round(ga["leads"] * share, 1) if share is not None else None
    gb = bk["google_ads"] if bk else None
    stages = [
        Stage("impressions", "Ad impressions", ads["impressions"] if ads else None, "Google Ads"),
        Stage("clicks", "Ad clicks", ads["clicks"] if ads else None, "Google Ads"),
        Stage("visits", "Paid visits", ga.get("paid_sessions") if ga.get("measured") else None, "GA4 · Paid Search sessions"),
        Stage("leads", "Leads", est_leads, "GA4 lead events × paid share of visits", estimated=True),
        Stage("bookings", "Bookings from Google Ads", gb["count"] if gb else None, "Bookings (gclid / utm google cpc)"),
        Stage("revenue", "Revenue from Google Ads", gb["revenue"] if gb else None, "Bookings (gclid / utm google cpc)"),
    ]
    cost = ads["cost"] if ads else None
    last = None
    for s in stages:
        if s.key != "impressions" and last is not None and s.value is not None and s.key != "revenue":
            s.rate = _div(s.value, last.value)
        if s.key in ("clicks", "visits", "leads", "bookings") and cost and s.value:
            s.cost_per = round(cost / s.value, 2)
        if s.key == "visits" and ga4_partial:
            s.rate = None  # GA4 covers only part of the period: clicks and visits aren't comparable
        if s.value is not None and s.key != "revenue":
            last = s
        if prev and prev.get(s.key) is not None and s.value is not None:
            s.previous = prev[s.key]
            s.change = _div(s.value - prev[s.key], prev[s.key])
    return stages


def bottlenecks(stages: list[Stage], ads: dict | None, ga: dict, bk: dict | None, *, ga4_from: str | None = None) -> list[Bottleneck]:
    st = {s.key: s for s in stages}
    out: list[Bottleneck] = []
    add = lambda *a, **k: out.append(Bottleneck(*a, **k))  # noqa: E731
    if ga4_from:
        add("ga4_partial", "info", "visits", f"GA4 data starts on {ga4_from}",
            "Ad clicks cover the whole period but GA4 visits only part of it, so click → visit isn't compared.",
            f"Pick a period starting on or after {ga4_from}.")
    if ads is None:
        add("no_ads_account", "critical", "clicks", "No Google Ads account linked to this website", "Ad stages can't be measured.",
            "Link the account under Websites.", "/websites")
    if not ga.get("measured"):
        add("no_ga4", "critical", "visits", "No GA4 data for this period", "Visits and leads can't be measured.",
            "Connect GA4 for this website and sync it (Conversions).", "/conversions")
    elif not ga.get("lead_events"):
        add("leads_not_measured", "critical", "leads", "No lead event in GA4",
            "No GA4 event is marked (or recognised) as a lead — form submissions, quote requests and calls are invisible.",
            "Send a GA4 event on successful quote/booking form submission and mark it as a lead in Conversions.", "/conversions")
    if bk is None or not bk["count"]:
        add("bookings_not_measured", "critical", "bookings", "No bookings imported",
            "Without booking data the funnel stops at leads: revenue, ROAS and booking rate are unknown.",
            "Import bookings (Conversions → Bookings) with gclid/utm, or connect the booking system.", "/conversions")
    elif not bk["google_ads"]["count"]:
        add("no_ads_bookings", "warning", "bookings", "No booking is attributed to Google Ads",
            "Bookings exist but none carries a gclid or utm_source=google / utm_medium=cpc.",
            "Capture gclid/utm on the booking form and pass it into the booking record.")
    ctr = st["clicks"].rate
    if ctr is not None and st["impressions"].value and st["impressions"].value >= 500 and ctr < BENCH["ctr"]:
        add("low_ctr", "warning", "clicks", f"Low click-through rate ({ctr:.1%})", "Ads are shown but rarely clicked.",
            "Tighten keywords and improve ad relevance.", "/ads-assets")
    vr = st["visits"].rate
    if vr is not None and st["clicks"].value and st["clicks"].value >= 30 and vr < BENCH["visit_rate"]:
        add("clicks_lost", "warning", "visits", f"Only {vr:.0%} of ad clicks arrive as GA4 paid visits",
            "Clicks are lost between the ad and the site: slow/broken landing pages, missing GA4 tag, consent banner, or auto-tagging off.",
            "Check landing pages and that Google Ads auto-tagging is on.", "/landing-pages")
    lr = st["leads"].rate
    if lr is not None and ga.get("lead_events") and st["visits"].value and st["visits"].value >= 50 and lr < BENCH["lead_rate"]:
        add("low_lead_rate", "warning", "leads", f"Low visit → lead rate ({lr:.1%}, estimated)", "Visitors arrive but few enquire.",
            "Fix the landing pages' CTA, form and trust issues.", "/landing-pages")
    br = st["bookings"].rate
    if br is not None and st["leads"].value and st["leads"].value >= 10 and br < BENCH["booking_rate"]:
        add("low_booking_rate", "warning", "bookings", f"Few leads become bookings ({br:.0%})", "Enquiries are not converting into bookings.",
            "Review quote speed, pricing and follow-up of enquiries.")
    rev, cost = st["revenue"].value, ads["cost"] if ads else None
    if rev is not None and cost and cost >= 100 and rev < cost:
        add("roas_below_1", "critical", "revenue", f"Google Ads revenue (AUD {rev:,.0f}) is below spend (AUD {cost:,.0f})",
            "The measured bookings don't pay for the ads.", "Cut wasted spend first (search terms, negatives), then fix conversion.", "/search-terms")
    if ga.get("unmapped"):
        add("unmapped_events", "info", "leads", "Some GA4 events are recognised by name but not confirmed",
            "Their role is guessed from the event name.", "Confirm the role of each event in Conversions.", "/conversions")
    return out


def to_dicts(items) -> list[dict]:
    return [asdict(i) for i in items]
