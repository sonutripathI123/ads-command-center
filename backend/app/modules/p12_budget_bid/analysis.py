"""P12 — pure analysis (no DB, no network): turns the pulled segment tables into plain-language findings.

Principles: observation (facts) is kept apart from the proposed action; every finding states how much data it rests on;
small samples are labelled `low` confidence and never phrased as certain. Nothing is applied anywhere — advice only.
"""
from dataclasses import dataclass, field

MIN_CLICKS = 30            # device / weekday / day-part
MIN_CLICKS_LOCATION = 15
WASTE_MIN_COST = 30.0      # AUD spent with no conversion before we call it out
WASTE_MIN_SHARE = 0.08     # ...and at least this share of all spend (location: 2%)
EXPENSIVE_FACTOR = 1.5     # CPA vs account average
EFFICIENT_FACTOR = 0.6
MIN_CONV_FOR_CPA = 3
EXPECTED_MIN = 3.0         # a 'no conversions' call needs >= 3 conversions expected at the account average (chance of 0 is then <= 5%)
HOME_REGION = "Victoria,Australia"
BUDGET_LOST_MIN = 0.15
RANK_LOST_MIN = 0.40
CAMPAIGN_WASTE_MIN = 150.0
DAYPARTS = (("Late night (12am-6am)", 0, 5), ("Morning (6am-12pm)", 6, 11), ("Afternoon (12pm-6pm)", 12, 17), ("Evening (6pm-12am)", 18, 23))
DEVICE_LABEL = {"MOBILE": "Mobile", "DESKTOP": "Desktop", "TABLET": "Tablet", "CONNECTED_TV": "Connected TV", "OTHER": "Other"}


@dataclass
class Finding:
    dimension: str
    segment: str
    code: str
    severity: str
    title: str
    observation: str
    evidence: list = field(default_factory=list)
    proposed_action: str = ""
    confidence: str = "low"


def cpa(row: dict) -> float | None:
    return row["cost"] / row["conversions"] if row["conversions"] > 0 else None


def totals(rows: list[dict]) -> dict:
    t = {"impressions": 0, "clicks": 0, "cost": 0.0, "conversions": 0.0, "value": 0.0}
    for r in rows:
        for k in t:
            t[k] += r[k]
    return t


def dayparts(hours: list[dict]) -> list[dict]:
    out = []
    for label, a, b in DAYPARTS:
        t = totals([h for h in hours if a <= int(h["key"]) <= b])
        out.append({"key": label, **t})
    return out


def _confidence(row: dict) -> str:
    return "medium" if row["conversions"] >= 10 and row["clicks"] >= 100 else "low"


def expected(row: dict, total: dict) -> float:
    return row["clicks"] * total["conversions"] / total["clicks"] if total["clicks"] else 0.0


def _ev(row: dict, total: dict, avg: float | None) -> list:
    c = cpa(row)
    return [["Spend", f"AUD {row['cost']:.2f} ({row['cost'] / total['cost']:.0%} of total)"], ["Clicks", str(row["clicks"])],
            ["Conversions", f"{row['conversions']:.1f}"], ["Cost per conversion", f"AUD {c:.2f}" if c else "none yet"],
            ["Account average", f"AUD {avg:.2f}" if avg else "n/a"],
            ["Conversions expected at the account average", f"{expected(row, total):.1f}"]]


ACTIONS = {
    "device": {"waste": "Lower the bid for this device (for example -20% to -30%) and watch for 2 weeks.",
               "expensive": "Lower the bid adjustment for this device a little (-10% to -20%).",
               "efficient": "Consider a positive bid adjustment (+10% to +20%) for this device."},
    "day": {"waste": "Use an ad schedule to lower bids on this day (-20% to -30%), or turn it off if it stays empty.",
            "expensive": "Lower bids a little on this day.",
            "efficient": "Raise bids a little on this day, or make sure budget doesn't run out before it."},
    "daypart": {"waste": "Add an ad schedule that lowers bids for this part of the day (or turns it off if bookings never come at this time).",
                "expensive": "Lower bids a little for this part of the day.",
                "efficient": "Raise bids a little for this part of the day, and keep budget for it."},
    "location": {"waste": "Lower the bid for this location, or exclude it if it's outside the area you serve.",
                 "expensive": "Lower the bid for this location.", "efficient": "Raise the bid for this location."},
}


def segment_findings(dim: str, rows: list[dict], total: dict, avg: float | None, label=lambda r: r["key"]) -> list[Finding]:
    out: list[Finding] = []
    min_clicks = MIN_CLICKS_LOCATION if dim == "location" else MIN_CLICKS
    share_min = 0.02 if dim == "location" else WASTE_MIN_SHARE
    for r in rows:
        if r["clicks"] < min_clicks or total["cost"] <= 0:
            continue
        name, c, share = label(r), cpa(r), r["cost"] / total["cost"]
        home = dim == "location" and (r.get("canonical") or "").endswith(HOME_REGION)
        if r["conversions"] == 0 and r["cost"] >= WASTE_MIN_COST and share >= share_min and expected(r, total) >= EXPECTED_MIN:
            out.append(Finding(dim, name, "no_conversions", "info" if home else "warning", f"{name}: AUD {r['cost']:.0f} spent, no conversions",
                               f"{name} took {share:.0%} of spend ({r['clicks']} clicks) and produced no conversion in this period.",
                               _ev(r, total, avg),
                               "Inside your home region, so don't cut it on this evidence; check that the ad and landing page suit people searching from here." if home
                               else ACTIONS[dim]["waste"], "low"))
        elif c and avg and r["conversions"] >= MIN_CONV_FOR_CPA and c >= avg * EXPENSIVE_FACTOR:
            out.append(Finding(dim, name, "expensive", "warning", f"{name}: conversions cost {c / avg:.1f}x the average",
                               f"{name} costs AUD {c:.0f} per conversion against an account average of AUD {avg:.0f}.",
                               _ev(r, total, avg), ACTIONS[dim]["expensive"], _confidence(r)))
        elif c and avg and r["conversions"] >= MIN_CONV_FOR_CPA and c <= avg * EFFICIENT_FACTOR:
            out.append(Finding(dim, name, "efficient", "info", f"{name}: conversions cost only {c / avg:.1f}x the average",
                               f"{name} costs AUD {c:.0f} per conversion against an account average of AUD {avg:.0f}.",
                               _ev(r, total, avg), ACTIONS[dim]["efficient"], _confidence(r)))
    return out


def location_extras(rows: list[dict], total: dict, not_served: list[str]) -> list[Finding]:
    out = []
    abroad = [r for r in rows if r["canonical"] and not r["canonical"].endswith("Australia")]
    cost = sum(r["cost"] for r in abroad)
    if cost >= 10:
        out.append(Finding("location", "Outside Australia", "outside_country", "warning", f"AUD {cost:.0f} spent on clicks from outside Australia",
                           f"{sum(r['clicks'] for r in abroad)} clicks came from {len(abroad)} places outside Australia.",
                           [["Spend", f"AUD {cost:.2f}"], ["Places", "; ".join((r["canonical"] or r["label"]).replace(",", ", ")[:45] for r in abroad[:4])]],
                           "In Google Ads location options choose 'Presence' (people in your locations) instead of 'Presence or interest'.", "medium"))
    low = [n.lower() for n in not_served]
    for r in rows:
        if r["cost"] >= 5 and any(n and n in (r["canonical"] or r["label"]).lower() for n in low):
            out.append(Finding("location", r["label"], "not_served", "warning", f"Spending on {r['label']}, which you marked as not served",
                               f"{r['label']} matches a place in your Business Rules 'not served' list.",
                               [["Spend", f"AUD {r['cost']:.2f}"], ["Clicks", str(r["clicks"])]],
                               "Exclude this location in Google Ads.", "medium"))
    return out


def budget_findings(campaigns: list[dict], target_cpa: float | None, account_avg: float | None) -> list[Finding]:
    out = []
    for c in campaigns:
        if c["status"] != "ENABLED":
            continue
        n, cpc = c["campaign"], cpa({"cost": c["cost"], "conversions": c["conversions"]})
        ev = [["Daily budget", f"AUD {c['daily_budget']:.2f}"], ["Spend", f"AUD {c['cost']:.2f}"], ["Conversions", f"{c['conversions']:.1f}"],
              ["Impression share", f"{c['impression_share']:.0%}" if c["impression_share"] else "n/a"],
              ["Lost to budget", f"{c['lost_budget']:.0%}" if c["lost_budget"] else "0%"],
              ["Lost to ad rank", f"{c['lost_rank']:.0%}" if c["lost_rank"] else "0%"], ["Bid strategy", c["bidding"]]]
        good = c["conversions"] > 0 and (cpc is None or (target_cpa and cpc <= target_cpa) or (not target_cpa and account_avg and cpc <= account_avg * 1.2))
        if (c["lost_budget"] or 0) >= BUDGET_LOST_MIN:
            if good:
                out.append(Finding("budget", n, "budget_limited", "warning", f"{n}: losing {c['lost_budget']:.0%} of searches because the budget runs out",
                                   "Converting well enough, but the daily budget ends before the day does.", ev,
                                   "Raise the daily budget (for example +20%) and check it again in a week.", "low"))
            else:
                out.append(Finding("budget", n, "budget_limited_unproven", "info", f"{n}: budget runs out ({c['lost_budget']:.0%} of searches lost) but results aren't proven",
                                   "Don't raise the budget yet: conversions are too few or too expensive to justify more spend.", ev,
                                   "Fix tracking and wasted searches first, then reconsider the budget.", "low"))
        if (c["lost_rank"] or 0) >= RANK_LOST_MIN:
            out.append(Finding("budget", n, "rank_limited", "warning", f"{n}: losing {c['lost_rank']:.0%} of searches on ad rank, not budget",
                               "Ads are shown less because bids or ad/landing-page quality rank below competitors.", ev,
                               "Improve ad relevance and landing page first (Quality Score); raise bids only for keywords that convert.", "low"))
        if c["cost"] >= CAMPAIGN_WASTE_MIN and c["conversions"] == 0:
            out.append(Finding("budget", n, "spend_no_conversions", "warning", f"{n}: AUD {c['cost']:.0f} spent, no conversions yet",
                               "No conversion recorded for this campaign in this period (check that conversion tracking is working before judging it).", ev,
                               "Review its search terms and negatives; consider pausing keywords that spend without converting.", "low"))
        if c["bidding"] in ("TARGET_SPEND", "MAXIMIZE_CLICKS") and c["cost"] >= 100:
            out.append(Finding("budget", n, "maximize_clicks", "info", f"{n}: bidding is set to get clicks, not bookings",
                               "'Maximize clicks' buys as many clicks as the budget allows, whether or not they turn into bookings.", ev,
                               "Once conversion tracking is reliable, consider Maximize conversions (optionally with a target cost per conversion).", "low"))
    return out


def analyse(data: dict, *, target_cpa: float | None = None, not_served: list[str] | None = None) -> tuple[list[Finding], dict]:
    parts = dayparts(data["hour"])
    total = totals(data["device"])
    avg = cpa(total)
    meta = {"total": total, "average_cpa": avg, "dayparts": parts}
    if total["cost"] <= 0:
        return [], meta
    if total["conversions"] == 0:
        return [Finding("device", "Account", "no_conversions_at_all", "info", "No conversions recorded in this period",
                        "Without any conversion, nothing can be said about which device, day, time or place works best.", [],
                        "Fix conversion tracking first, then run this analysis again.", "low")] + budget_findings(data["campaigns"], target_cpa, avg), meta
    out: list[Finding] = []
    out += segment_findings("device", data["device"], total, avg, lambda r: DEVICE_LABEL.get(r["key"], r["key"].title()))
    out += segment_findings("day", data["day"], total, avg, lambda r: r["key"].title())
    out += segment_findings("daypart", parts, total, avg)
    out += segment_findings("location", data["location"], total, avg, lambda r: f"{r['label']} ({r['type'].lower()})" if r["type"] else r["label"])
    out += location_extras(data["location"], total, not_served or [])
    out += budget_findings(data["campaigns"], target_cpa, avg)
    order = {"warning": 0, "info": 1}
    return sorted(out, key=lambda f: order[f.severity]), meta
