"""P19 — report periods and content. Account report: KPIs vs previous period, campaigns, top search terms, funnel of
linked websites, open recommendations, approval decisions, open alerts. Website report: GA4, Search Console, bookings,
tracking health, funnel. Everything comes from other modules' public interfaces; nothing here computes new facts."""
import calendar
from datetime import date, timedelta

KPI = [("impressions", "Impressions"), ("clicks", "Clicks"), ("cost", "Cost (AUD)"), ("conversions", "Conversions"),
       ("conversions_value", "Conv. value (AUD)"), ("ctr", "CTR"), ("avg_cpc", "Avg. CPC (AUD)"), ("cost_per_conversion", "Cost / conv. (AUD)")]
PERIODS = ("daily", "weekly", "monthly", "custom")


def period(kind: str, today: date, d1: date | None = None, d2: date | None = None) -> tuple[date, date, str]:
    y = today - timedelta(days=1)
    if kind == "daily":
        return y, y, y.strftime("%a %d %b %Y")
    if kind == "weekly":
        return y - timedelta(days=6), y, f"Week to {y:%d %b %Y}"
    if kind == "monthly":
        last = today.replace(day=1) - timedelta(days=1)
        return last.replace(day=1), last, last.strftime("%B %Y")
    if kind == "custom":
        if not d1 or not d2 or d1 > d2 or (d2 - d1).days > 730:
            raise ValueError("Custom period needs from ≤ to, up to 2 years")
        return d1, d2, f"{d1:%d %b %Y} – {d2:%d %b %Y}"
    raise ValueError(f"period must be one of {PERIODS}")


def previous(d1: date, d2: date, kind: str) -> tuple[date, date]:
    if kind == "monthly":
        last = d1 - timedelta(days=1)
        return last.replace(day=1), last.replace(day=calendar.monthrange(last.year, last.month)[1])
    n = (d2 - d1).days + 1
    return d1 - timedelta(days=n), d1 - timedelta(days=1)


def kpis(now: dict, prev: dict) -> list[dict]:
    out = []
    for k, label in KPI:
        a, b = now.get(k), prev.get(k)
        change = round((a - b) / b, 4) if a is not None and b else None
        out.append({"key": k, "label": label, "value": a, "previous": b, "change": change})
    return out


def headline(k: list[dict]) -> list[str]:
    """Plain-English summary lines from the KPI changes (facts only)."""
    by = {x["key"]: x for x in k}
    lines = []
    c = by["cost"]
    if c["value"] is not None:
        lines.append(f"Spend AUD {c['value']:,.2f}" + (f" ({c['change']:+.0%} vs previous period)." if c["change"] is not None else "."))
    cl, cv = by["clicks"], by["conversions"]
    if cl["value"] is not None:
        lines.append(f"{cl['value']:,} clicks and {cv['value']:g} conversions" +
                     (f" (conversions {cv['change']:+.0%})." if cv["change"] is not None else "."))
    cpa = by["cost_per_conversion"]
    if cpa["value"]:
        lines.append(f"Cost per conversion AUD {cpa['value']:,.2f}" + (f" ({cpa['change']:+.0%})." if cpa["change"] is not None else "."))
    return lines
