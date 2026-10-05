"""P12 — READ-ONLY Google Ads pulls (GAQL SELECT through P04's ReadSession) → plain, aggregated dicts.
Account-level tables for device / day of week / hour / location, plus per-campaign budget & impression-share rows."""
from collections import defaultdict
from datetime import date

DAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")
_M = "metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.conversions_value"


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _blank() -> dict:
    return {"impressions": 0, "clicks": 0, "cost": 0.0, "conversions": 0.0, "value": 0.0}


def _add(into: dict, m: dict) -> None:
    into["impressions"] += int(_num(m.get("impressions")))
    into["clicks"] += int(_num(m.get("clicks")))
    into["cost"] += _num(m.get("costMicros")) / 1_000_000
    into["conversions"] += _num(m.get("conversions"))
    into["value"] += _num(m.get("conversionsValue"))


def _group(rows: list[dict], keyfn) -> list[dict]:
    acc: dict[str, dict] = defaultdict(_blank)
    for r in rows:
        k = keyfn(r)
        if k is not None:
            _add(acc[str(k)], r.get("metrics", {}))
    return [{"key": k, **v} for k, v in acc.items()]


def _window(d1: date, d2: date) -> str:
    return f"segments.date BETWEEN '{d1.isoformat()}' AND '{d2.isoformat()}'"


def locations(session, rows: list[dict]) -> list[dict]:
    """Resolve geoTargetConstants/<id> to readable names (only for places that actually got clicks)."""
    grouped = [g for g in _group(rows, lambda r: r.get("segments", {}).get("geoTargetMostSpecificLocation")) if g["clicks"] > 0]
    ids = [g["key"] for g in grouped]
    names: dict[str, dict] = {}
    for i in range(0, len(ids), 100):
        chunk = ",".join(f"'{x}'" for x in ids[i:i + 100])
        for r in session.search("SELECT geo_target_constant.resource_name, geo_target_constant.name, geo_target_constant.canonical_name, "
                                f"geo_target_constant.target_type FROM geo_target_constant WHERE geo_target_constant.resource_name IN ({chunk})"):
            c = r.get("geoTargetConstant", {})
            names[c.get("resourceName", "")] = c
    out = []
    for g in grouped:
        c = names.get(g["key"], {})
        out.append({**g, "label": c.get("name") or g["key"], "canonical": c.get("canonicalName") or "", "type": c.get("targetType") or ""})
    return sorted(out, key=lambda r: -r["cost"])


def pull(session, d1: date, d2: date) -> dict:
    w = _window(d1, d2)
    device = _group(session.search(f"SELECT segments.device, {_M} FROM campaign WHERE {w}"), lambda r: r["segments"].get("device"))
    dow = _group(session.search(f"SELECT segments.day_of_week, {_M} FROM campaign WHERE {w}"), lambda r: r["segments"].get("dayOfWeek"))
    hour = _group(session.search(f"SELECT segments.hour, {_M} FROM campaign WHERE {w}"), lambda r: r["segments"].get("hour"))
    geo_rows = session.search(f"SELECT segments.geo_target_most_specific_location, {_M} FROM user_location_view WHERE {w}")
    budget = []
    for r in session.search("SELECT campaign.id, campaign.name, campaign.status, campaign.bidding_strategy_type, campaign_budget.amount_micros, "
                            "metrics.search_impression_share, metrics.search_budget_lost_impression_share, metrics.search_rank_lost_impression_share, "
                            "metrics.cost_micros, metrics.conversions, metrics.clicks "
                            f"FROM campaign WHERE {w} AND campaign.status != 'REMOVED'"):
        m, c = r.get("metrics", {}), r.get("campaign", {})
        budget.append({"campaign": c.get("name", ""), "status": c.get("status", ""), "bidding": c.get("biddingStrategyType", ""),
                       "daily_budget": _num(r.get("campaignBudget", {}).get("amountMicros")) / 1_000_000,
                       "cost": _num(m.get("costMicros")) / 1_000_000, "conversions": _num(m.get("conversions")),
                       "clicks": int(_num(m.get("clicks"))), "impression_share": _num(m.get("searchImpressionShare")) or None,
                       "lost_budget": _num(m.get("searchBudgetLostImpressionShare")) or None,
                       "lost_rank": _num(m.get("searchRankLostImpressionShare")) or None})
    # several rows per campaign (one per day) are merged by name: spend/conversions add up, the share metrics are averaged by cost
    merged: dict[str, dict] = {}
    for b in budget:
        t = merged.setdefault(b["campaign"], {**b, "cost": 0.0, "conversions": 0.0, "clicks": 0, "_w": 0.0, "_is": 0.0, "_lb": 0.0, "_lr": 0.0})
        t["cost"] += b["cost"]; t["conversions"] += b["conversions"]; t["clicks"] += b["clicks"]
        t["status"], t["daily_budget"], t["bidding"] = b["status"], b["daily_budget"], b["bidding"]
        wgt = b["cost"] or 0.0001
        t["_w"] += wgt
        for src, dst in (("impression_share", "_is"), ("lost_budget", "_lb"), ("lost_rank", "_lr")):
            t[dst] += (b[src] or 0) * wgt
    camps = []
    for t in merged.values():
        wsum = t.pop("_w") or 1
        for src, dst in (("impression_share", "_is"), ("lost_budget", "_lb"), ("lost_rank", "_lr")):
            t[src] = round(t.pop(dst) / wsum, 4) or None
        camps.append(t)
    return {"device": device, "day": sorted(dow, key=lambda r: DAYS.index(r["key"]) if r["key"] in DAYS else 9),
            "hour": sorted(hour, key=lambda r: int(r["key"])), "location": locations(session, geo_rows),
            "campaigns": sorted(camps, key=lambda r: -r["cost"])}
