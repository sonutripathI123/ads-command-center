"""P18 — pure monitoring checks. Recent = last 7 days; baseline = the 28 days before (as a weekly average).
Thresholds are deliberately conservative so alerts stay rare and meaningful."""
from dataclasses import asdict, dataclass
from datetime import date, timedelta

RECENT_DAYS, BASE_DAYS = 7, 28
MIN_SPEND, MIN_CLICKS, MIN_IMPR = 50.0, 30, 1000


@dataclass
class Signal:
    code: str
    severity: str        # critical | warning | info
    title: str
    detail: str
    action: str
    evidence: list
    link: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def windows(today: date) -> tuple[date, date, date, date]:
    r2 = today - timedelta(days=1)  # yesterday: today's data is incomplete
    r1 = r2 - timedelta(days=RECENT_DAYS - 1)
    b2 = r1 - timedelta(days=1)
    return r1, r2, b2 - timedelta(days=BASE_DAYS - 1), b2


def _sum(days: list[dict], k: str) -> float:
    return sum(d[k] or 0 for d in days)


def _pct(a: float, b: float) -> float | None:
    return (a - b) / b if b else None


def evaluate(daily: list[dict], today: date, *, new_terms: list[dict], recent_term_cost: float,
             tracking: list[dict]) -> list[Signal]:
    """daily: P05 summary daily rows (date iso, impressions, clicks, cost, conversions) covering baseline + recent."""
    r1, r2, b1, b2 = windows(today)
    rec = [d for d in daily if r1.isoformat() <= d["date"] <= r2.isoformat()]
    base = [d for d in daily if b1.isoformat() <= d["date"] <= b2.isoformat()]
    k = RECENT_DAYS / BASE_DAYS
    rc, bc = _sum(rec, "cost"), _sum(base, "cost") * k
    rk, bk = _sum(rec, "clicks"), _sum(base, "clicks") * k
    ri, bi = _sum(rec, "impressions"), _sum(base, "impressions") * k
    rv, bv = _sum(rec, "conversions"), _sum(base, "conversions") * k
    ev = lambda: [["Last 7 days", f"AUD {rc:,.2f} · {rk:.0f} clicks · {rv:.1f} conv."],  # noqa: E731
                  ["Weekly avg (28 days before)", f"AUD {bc:,.2f} · {bk:.0f} clicks · {bv:.1f} conv."]]
    out: list[Signal] = []
    if rc >= MIN_SPEND and bc and rc >= 1.5 * bc:
        out.append(Signal("spend_spike", "critical" if rc >= 2.5 * bc else "warning", f"Spend up {_pct(rc, bc):.0%} this week",
                          "Spend is well above the recent weekly average.", "Check budgets, bid changes and new search terms.", ev(), "/campaigns"))
    if bc >= MIN_SPEND and rc == 0:
        out.append(Signal("spend_stopped", "warning", "Ads stopped spending", "No spend in the last 7 days after regular spend before.",
                          "Check whether campaigns were paused, budgets ran out or billing failed.", ev(), "/campaigns"))
    if bv >= 3 and rv <= 0.5 * bv:
        out.append(Signal("conversion_drop", "critical" if rv == 0 else "warning", f"Conversions down {abs(_pct(rv, bv) or 0):.0%}",
                          "Far fewer conversions than usual.", "Check conversion tracking first (a broken tag looks the same), then landing pages.",
                          ev(), "/conversions"))
    if rk >= MIN_CLICKS and bk >= MIN_CLICKS:
        rcpc, bcpc = rc / rk, (bc / bk if bk else 0)
        ch = _pct(rcpc, bcpc)
        if ch is not None and abs(ch) >= 0.3:
            out.append(Signal("cpc_change", "warning" if ch > 0 else "info", f"Average CPC {'up' if ch > 0 else 'down'} {abs(ch):.0%}",
                              f"AUD {rcpc:.2f} this week vs AUD {bcpc:.2f} usually.",
                              "Rising CPC: check competition, bid strategy and Quality Score." if ch > 0 else "Cheaper clicks — check they still convert.",
                              ev(), "/keywords"))
    if ri >= MIN_IMPR and bi >= MIN_IMPR and bk:
        rctr, bctr = rk / ri, bk / bi
        if bctr and (rctr - bctr) / bctr <= -0.3:
            out.append(Signal("ctr_drop", "warning", f"CTR down {abs((rctr - bctr) / bctr):.0%}", f"{rctr:.1%} this week vs {bctr:.1%} usually.",
                              "Check ad copy, new competitors and irrelevant search terms.", ev(), "/ads-assets"))
    last3 = [d for d in daily if d["date"] > (r2 - timedelta(days=3)).isoformat() and d["date"] <= r2.isoformat()]
    if bi and not _sum(last3, "impressions"):
        out.append(Signal("no_recent_data", "info", "No ad activity in the last 3 days",
                          "Either the campaigns are paused or the Google Ads data hasn't been synced.",
                          "Sync the account (Ads Accounts) or check campaign status.", [], "/ads-accounts"))
    if new_terms and recent_term_cost:
        new_cost = sum(t["cost"] for t in new_terms)
        if new_cost >= 20 and new_cost / recent_term_cost >= 0.3:
            out.append(Signal("search_term_shift", "warning", f"{new_cost / recent_term_cost:.0%} of this week's spend went to new search terms",
                              "Searches you haven't paid for before are taking a big share of spend.", "Review them and add negatives where irrelevant.",
                              [[t["search_term"], f"AUD {t['cost']:.2f} · {t['clicks']} clicks · {t['conversions']} conv."]
                               for t in sorted(new_terms, key=lambda t: -t["cost"])[:8]], "/search-terms"))
    for h in tracking:
        if h["severity"] == "critical":
            out.append(Signal(f"tracking:{h['code']}", "critical", f"Tracking: {h['title']}", h.get("detail", ""),
                              "Fix conversion tracking — every other number depends on it.", [], "/conversions"))
    return out
