"""P05 — read queries over the warehouse (aggregations for pages and for other modules via interface.py)."""
import json
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.modules.p05_ads_sync.models import Ad, AdGroup, Campaign, Keyword, MetricsSnapshot, SearchTerm, SyncRun

STALE_RUN = timedelta(minutes=30)

_SUMS = (func.sum(MetricsSnapshot.impressions), func.sum(MetricsSnapshot.clicks), func.sum(MetricsSnapshot.cost_micros),
         func.sum(MetricsSnapshot.conversions), func.sum(MetricsSnapshot.conversions_value))


def derive(impressions: int, clicks: int, cost_micros: int, conversions: float, value: float) -> dict:
    cost = cost_micros / 1_000_000
    return {
        "impressions": int(impressions or 0), "clicks": int(clicks or 0), "cost": round(cost, 2),
        "conversions": round(conversions or 0, 2), "conversions_value": round(value or 0, 2),
        "ctr": round(clicks / impressions, 4) if impressions else None,
        "avg_cpc": round(cost / clicks, 2) if clicks else None,
        "conv_rate": round(conversions / clicks, 4) if clicks else None,
        "cost_per_conversion": round(cost / conversions, 2) if conversions else None,
    }


def _metric_totals(db: DbSession, account_id: int, entity_type: str, d1: date, d2: date,
                   keys: list[str] | None = None) -> dict[str, dict]:
    q = (select(MetricsSnapshot.entity_key, *_SUMS)
         .where(MetricsSnapshot.account_id == account_id, MetricsSnapshot.entity_type == entity_type,
                MetricsSnapshot.date >= d1, MetricsSnapshot.date <= d2)
         .group_by(MetricsSnapshot.entity_key))
    if keys is not None:
        q = q.where(MetricsSnapshot.entity_key.in_(keys))
    return {k: derive(*vals) for k, *vals in db.execute(q)}


def _empty() -> dict:
    return derive(0, 0, 0, 0.0, 0.0)


def summary(db: DbSession, account_id: int, d1: date, d2: date) -> dict:
    q = (select(MetricsSnapshot.date, *_SUMS)
         .where(MetricsSnapshot.account_id == account_id, MetricsSnapshot.entity_type == "campaign",
                MetricsSnapshot.date >= d1, MetricsSnapshot.date <= d2)
         .group_by(MetricsSnapshot.date).order_by(MetricsSnapshot.date))
    by_day = {d: derive(*vals) for d, *vals in db.execute(q)}
    daily, day = [], d1
    while day <= d2:
        daily.append({"date": day.isoformat(), **by_day.get(day, _empty())})
        day += timedelta(days=1)
    t = [sum(x[f] for x in daily) for f in ("impressions", "clicks")]
    cost_micros = round(sum(x["cost"] for x in daily) * 1_000_000)
    conv, value = sum(x["conversions"] for x in daily), sum(x["conversions_value"] for x in daily)
    return {"totals": derive(t[0], t[1], cost_micros, conv, value), "daily": daily}


def campaigns(db: DbSession, account_id: int, d1: date, d2: date) -> list[dict]:
    m = _metric_totals(db, account_id, "campaign", d1, d2)
    out = [{"google_id": c.google_id, "name": c.name, "status": c.status, "channel_type": c.channel_type,
            "bidding_strategy_type": c.bidding_strategy_type,
            "budget": round(c.budget_micros / 1_000_000, 2) if c.budget_micros else None,
            **m.get(c.google_id, _empty())}
           for c in db.scalars(select(Campaign).where(Campaign.account_id == account_id))]
    return sorted(out, key=lambda r: -r["cost"])


def _campaign_names(db: DbSession, account_id: int) -> dict[str, str]:
    return {c.google_id: c.name for c in db.scalars(select(Campaign).where(Campaign.account_id == account_id))}


def _ad_group_names(db: DbSession, account_id: int) -> dict[str, str]:
    return {g.google_id: g.name for g in db.scalars(select(AdGroup).where(AdGroup.account_id == account_id))}


def ad_groups(db: DbSession, account_id: int, d1: date, d2: date, campaign_id: str | None = None) -> list[dict]:
    q = select(AdGroup).where(AdGroup.account_id == account_id)
    if campaign_id:
        q = q.where(AdGroup.campaign_google_id == campaign_id)
    m, names = _metric_totals(db, account_id, "ad_group", d1, d2), _campaign_names(db, account_id)
    out = [{"google_id": g.google_id, "name": g.name, "status": g.status, "type": g.type,
            "campaign_google_id": g.campaign_google_id, "campaign_name": names.get(g.campaign_google_id, ""),
            **m.get(g.google_id, _empty())} for g in db.scalars(q)]
    return sorted(out, key=lambda r: -r["cost"])


def keywords(db: DbSession, account_id: int, d1: date, d2: date, campaign_id: str | None = None,
             ad_group_id: str | None = None) -> list[dict]:
    q = select(Keyword).where(Keyword.account_id == account_id)
    if campaign_id:
        q = q.where(Keyword.campaign_google_id == campaign_id)
    if ad_group_id:
        q = q.where(Keyword.ad_group_google_id == ad_group_id)
    m = _metric_totals(db, account_id, "keyword", d1, d2)
    cn, gn = _campaign_names(db, account_id), _ad_group_names(db, account_id)
    out = [{"key": k.key, "text": k.text, "match_type": k.match_type, "status": k.status,
            "quality_score": k.quality_score, "campaign_google_id": k.campaign_google_id,
            "campaign_name": cn.get(k.campaign_google_id, ""), "ad_group_google_id": k.ad_group_google_id,
            "ad_group_name": gn.get(k.ad_group_google_id, ""), **m.get(k.key, _empty())} for k in db.scalars(q)]
    return sorted(out, key=lambda r: -r["cost"])


def search_terms(db: DbSession, account_id: int, d1: date, d2: date, *, q: str | None = None,
                 campaign_id: str | None = None, limit: int = 500) -> list[dict]:
    m = _metric_totals(db, account_id, "search_term", d1, d2)
    stmt = select(SearchTerm).where(SearchTerm.account_id == account_id, SearchTerm.key.in_(list(m)))
    if campaign_id:
        stmt = stmt.where(SearchTerm.campaign_google_id == campaign_id)
    if q:
        stmt = stmt.where(SearchTerm.search_term.ilike(f"%{q}%"))
    cn, gn = _campaign_names(db, account_id), _ad_group_names(db, account_id)
    out = [{"key": s.key, "search_term": s.search_term, "status": s.status, "matched_keyword": s.matched_keyword,
            "matched_match_type": s.matched_match_type, "campaign_google_id": s.campaign_google_id,
            "campaign_name": cn.get(s.campaign_google_id, ""), "ad_group_google_id": s.ad_group_google_id,
            "ad_group_name": gn.get(s.ad_group_google_id, ""),
            "first_seen": s.first_seen.isoformat() if s.first_seen else None, **m[s.key]}
           for s in db.scalars(stmt)]
    return sorted(out, key=lambda r: (-r["cost"], -r["clicks"]))[:limit]


def ads(db: DbSession, account_id: int, d1: date, d2: date) -> list[dict]:
    m = _metric_totals(db, account_id, "ad", d1, d2)
    cn, gn = _campaign_names(db, account_id), _ad_group_names(db, account_id)
    out = [{"key": a.key, "ad_id": a.ad_id, "type": a.type, "status": a.status,
            "final_urls": json.loads(a.final_urls), "headlines": json.loads(a.headlines),
            "descriptions": json.loads(a.descriptions), "campaign_name": cn.get(a.campaign_google_id, ""),
            "ad_group_name": gn.get(a.ad_group_google_id, ""), **m.get(a.key, _empty())}
           for a in db.scalars(select(Ad).where(Ad.account_id == account_id))]
    return sorted(out, key=lambda r: -r["cost"])


def runs(db: DbSession, account_id: int, limit: int = 10) -> list[SyncRun]:
    expire_stale(db)
    return list(db.scalars(select(SyncRun).where(SyncRun.account_id == account_id)
                           .order_by(SyncRun.id.desc()).limit(limit)))


def running(db: DbSession, account_id: int) -> SyncRun | None:
    expire_stale(db)
    return db.scalars(select(SyncRun).where(SyncRun.account_id == account_id, SyncRun.status == "running")).first()


def expire_stale(db: DbSession) -> None:
    """A run still 'running' after 30 minutes was interrupted (e.g. server restart)."""
    cutoff = datetime.now(UTC) - STALE_RUN
    changed = False
    for r in db.scalars(select(SyncRun).where(SyncRun.status == "running")):
        started = r.started_at if r.started_at.tzinfo else r.started_at.replace(tzinfo=UTC)
        if started < cutoff:
            r.status, r.finished_at = "failed", datetime.now(UTC)
            r.errors = json.dumps({"interrupted": "Sync did not finish (server restarted?)"})
            changed = True
    if changed:
        db.commit()
