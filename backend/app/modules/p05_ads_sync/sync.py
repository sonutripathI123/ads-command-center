"""P05 — sync engine. Pulls entities + daily metrics with GAQL SELECT queries through P04's ReadSession.

Each step is independent: a failing step (e.g. a field Google rejects) is recorded in the run and the
others continue. Metrics for the synced date window are replaced (delete + insert), so re-running is safe.
"""
import json
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.modules.p04_ads_connection.interface import AccountRef, active_accounts, open_read_session
from app.modules.p05_ads_sync.models import Ad, AdGroup, Campaign, Keyword, MetricsSnapshot, SearchTerm, SyncRun
from app.shared.db import session_scope
from app.shared.logging import get_logger

MODULE_ID = "P05"
INITIAL_DAYS = 90
LOOKBACK_DAYS = 3  # conversions keep arriving for a few days; re-pull them
log = get_logger(MODULE_ID)

METRICS = "metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.conversions_value"


def _g(row: dict, *path, default=None):
    for p in path:
        if not isinstance(row, dict) or p not in row:
            return default
        row = row[p]
    return row


def _metrics(row: dict) -> dict:
    m = row.get("metrics", {})
    return {"impressions": int(m.get("impressions", 0)), "clicks": int(m.get("clicks", 0)),
            "cost_micros": int(m.get("costMicros", 0)), "conversions": float(m.get("conversions", 0)),
            "conversions_value": float(m.get("conversionsValue", 0))}


def _between(d1: date, d2: date) -> str:
    return f"segments.date BETWEEN '{d1.isoformat()}' AND '{d2.isoformat()}'"


def _replace_metrics(db: DbSession, account_id: int, entity_type: str, d1: date, d2: date,
                     rows: dict[tuple[str, str], dict]) -> int:
    db.execute(delete(MetricsSnapshot).where(MetricsSnapshot.account_id == account_id,
                                             MetricsSnapshot.entity_type == entity_type,
                                             MetricsSnapshot.date >= d1, MetricsSnapshot.date <= d2))
    db.add_all(MetricsSnapshot(account_id=account_id, entity_type=entity_type, entity_key=k,
                               date=date.fromisoformat(d), **m) for (k, d), m in rows.items())
    return len(rows)


def _accumulate(target: dict, key: tuple[str, str], m: dict) -> None:
    cur = target.get(key)
    if cur is None:
        target[key] = dict(m)
    else:
        for f, v in m.items():
            cur[f] += v


def _upsert(db: DbSession, model, account_id: int, key_field: str, items: dict[str, dict]) -> int:
    existing = {getattr(o, key_field): o for o in
                db.scalars(select(model).where(model.account_id == account_id,
                                               getattr(model, key_field).in_(list(items))))} if items else {}
    for k, fields in items.items():
        obj = existing.get(k)
        if obj is None:
            db.add(model(account_id=account_id, **{key_field: k}, **fields))
        else:
            for f, v in fields.items():
                setattr(obj, f, v)
    return len(items)


# ---- steps ------------------------------------------------------------------------

def step_campaigns(db, rs, acc: AccountRef, d1, d2) -> int:
    rows = rs.search("SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, "
                     "campaign.bidding_strategy_type, campaign_budget.amount_micros FROM campaign "
                     "WHERE campaign.status != 'REMOVED'")
    items = {str(_g(r, "campaign", "id")): {
        "name": _g(r, "campaign", "name", default=""), "status": _g(r, "campaign", "status"),
        "channel_type": _g(r, "campaign", "advertisingChannelType"),
        "bidding_strategy_type": _g(r, "campaign", "biddingStrategyType"),
        "budget_micros": int(_g(r, "campaignBudget", "amountMicros", default=0) or 0) or None} for r in rows}
    n = _upsert(db, Campaign, acc.id, "google_id", items)
    mrows: dict = {}
    for r in rs.search(f"SELECT campaign.id, segments.date, {METRICS} FROM campaign WHERE {_between(d1, d2)}"):
        _accumulate(mrows, (str(_g(r, "campaign", "id")), _g(r, "segments", "date")), _metrics(r))
    return n + _replace_metrics(db, acc.id, "campaign", d1, d2, mrows)


def step_ad_groups(db, rs, acc, d1, d2) -> int:
    rows = rs.search("SELECT ad_group.id, ad_group.name, ad_group.status, ad_group.type, campaign.id "
                     "FROM ad_group WHERE ad_group.status != 'REMOVED'")
    items = {str(_g(r, "adGroup", "id")): {
        "campaign_google_id": str(_g(r, "campaign", "id")), "name": _g(r, "adGroup", "name", default=""),
        "status": _g(r, "adGroup", "status"), "type": _g(r, "adGroup", "type")} for r in rows}
    n = _upsert(db, AdGroup, acc.id, "google_id", items)
    mrows: dict = {}
    for r in rs.search(f"SELECT ad_group.id, segments.date, {METRICS} FROM ad_group WHERE {_between(d1, d2)}"):
        _accumulate(mrows, (str(_g(r, "adGroup", "id")), _g(r, "segments", "date")), _metrics(r))
    return n + _replace_metrics(db, acc.id, "ad_group", d1, d2, mrows)


def step_keywords(db, rs, acc, d1, d2) -> int:
    rows = rs.search("SELECT ad_group_criterion.criterion_id, ad_group_criterion.keyword.text, "
                     "ad_group_criterion.keyword.match_type, ad_group_criterion.status, "
                     "ad_group_criterion.quality_info.quality_score, ad_group.id, campaign.id "
                     "FROM keyword_view WHERE ad_group_criterion.status != 'REMOVED'")
    items = {}
    for r in rows:
        ag, crit = str(_g(r, "adGroup", "id")), str(_g(r, "adGroupCriterion", "criterionId"))
        items[f"{ag}~{crit}"] = {
            "campaign_google_id": str(_g(r, "campaign", "id")), "ad_group_google_id": ag, "criterion_id": crit,
            "text": _g(r, "adGroupCriterion", "keyword", "text", default=""),
            "match_type": _g(r, "adGroupCriterion", "keyword", "matchType"),
            "status": _g(r, "adGroupCriterion", "status"),
            "quality_score": _g(r, "adGroupCriterion", "qualityInfo", "qualityScore")}
    n = _upsert(db, Keyword, acc.id, "key", items)
    mrows: dict = {}
    for r in rs.search(f"SELECT ad_group_criterion.criterion_id, ad_group.id, segments.date, {METRICS} "
                       f"FROM keyword_view WHERE {_between(d1, d2)}"):
        key = f"{_g(r, 'adGroup', 'id')}~{_g(r, 'adGroupCriterion', 'criterionId')}"
        _accumulate(mrows, (key, _g(r, "segments", "date")), _metrics(r))
    return n + _replace_metrics(db, acc.id, "keyword", d1, d2, mrows)


def step_search_terms(db, rs, acc, d1, d2) -> int:
    rows = rs.search("SELECT search_term_view.search_term, search_term_view.status, ad_group.id, campaign.id, "
                     "segments.keyword.info.text, segments.keyword.info.match_type, segments.date, "
                     f"{METRICS} FROM search_term_view WHERE {_between(d1, d2)}")
    items: dict[str, dict] = {}
    mrows: dict = {}
    for r in rows:
        term, ag, day = _g(r, "searchTermView", "searchTerm", default=""), str(_g(r, "adGroup", "id")), _g(r, "segments", "date")
        key = f"{ag}~{term}"[:600]
        d = date.fromisoformat(day)
        cur = items.get(key)
        fields = {"search_term": term[:512], "campaign_google_id": str(_g(r, "campaign", "id")),
                  "ad_group_google_id": ag, "status": _g(r, "searchTermView", "status"),
                  "matched_keyword": _g(r, "segments", "keyword", "info", "text"),
                  "matched_match_type": _g(r, "segments", "keyword", "info", "matchType"),
                  "first_seen": d, "last_seen": d}
        if cur:
            fields["first_seen"], fields["last_seen"] = min(cur["first_seen"], d), max(cur["last_seen"], d)
        items[key] = fields
        _accumulate(mrows, (key, day), _metrics(r))
    # keep the earliest first_seen already stored
    for st in db.scalars(select(SearchTerm).where(SearchTerm.account_id == acc.id, SearchTerm.key.in_(list(items)))):
        if st.first_seen and st.first_seen < items[st.key]["first_seen"]:
            items[st.key]["first_seen"] = st.first_seen
    n = _upsert(db, SearchTerm, acc.id, "key", items)
    return n + _replace_metrics(db, acc.id, "search_term", d1, d2, mrows)


def step_ads(db, rs, acc, d1, d2) -> int:
    rows = rs.search("SELECT ad_group_ad.ad.id, ad_group_ad.ad.type, ad_group_ad.status, ad_group_ad.ad.final_urls, "
                     "ad_group_ad.ad.responsive_search_ad.headlines, ad_group_ad.ad.responsive_search_ad.descriptions, "
                     "ad_group.id, campaign.id FROM ad_group_ad WHERE ad_group_ad.status != 'REMOVED'")
    items = {}
    for r in rows:
        ag, ad_id = str(_g(r, "adGroup", "id")), str(_g(r, "adGroupAd", "ad", "id"))
        rsa = _g(r, "adGroupAd", "ad", "responsiveSearchAd", default={}) or {}
        items[f"{ag}~{ad_id}"] = {
            "campaign_google_id": str(_g(r, "campaign", "id")), "ad_group_google_id": ag, "ad_id": ad_id,
            "type": _g(r, "adGroupAd", "ad", "type"), "status": _g(r, "adGroupAd", "status"),
            "final_urls": json.dumps(_g(r, "adGroupAd", "ad", "finalUrls", default=[]) or []),
            "headlines": json.dumps([h.get("text", "") for h in rsa.get("headlines", [])]),
            "descriptions": json.dumps([d.get("text", "") for d in rsa.get("descriptions", [])])}
    n = _upsert(db, Ad, acc.id, "key", items)
    mrows: dict = {}
    for r in rs.search(f"SELECT ad_group_ad.ad.id, ad_group.id, segments.date, {METRICS} "
                       f"FROM ad_group_ad WHERE {_between(d1, d2)}"):
        key = f"{_g(r, 'adGroup', 'id')}~{_g(r, 'adGroupAd', 'ad', 'id')}"
        _accumulate(mrows, (key, _g(r, "segments", "date")), _metrics(r))
    return n + _replace_metrics(db, acc.id, "ad", d1, d2, mrows)


STEPS: list[tuple[str, Callable]] = [("campaigns", step_campaigns), ("ad_groups", step_ad_groups),
                                     ("keywords", step_keywords), ("search_terms", step_search_terms),
                                     ("ads", step_ads)]


# ---- runs ---------------------------------------------------------------------------

def account_today(acc: AccountRef) -> date:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(acc.time_zone or "Australia/Sydney")).date()
    except Exception:
        return datetime.now(timezone(timedelta(hours=10))).date()


def plan_window(db: DbSession, acc: AccountRef, days: int | None) -> tuple[date, date]:
    today = account_today(acc)
    if days:
        return today - timedelta(days=days - 1), today
    last = db.scalars(select(SyncRun).where(SyncRun.account_id == acc.id, SyncRun.status.in_(["success", "partial"]))
                      .order_by(SyncRun.id.desc()).limit(1)).first()
    if last is None:
        return today - timedelta(days=INITIAL_DAYS - 1), today
    return min(last.date_to, today) - timedelta(days=LOOKBACK_DAYS), today


def find_account(db: DbSession, account_id: int) -> AccountRef | None:
    return next((a for a in active_accounts(db) if a.id == account_id), None)


def start_run(db: DbSession, acc: AccountRef, *, days: int | None, user_id: int | None) -> SyncRun:
    d1, d2 = plan_window(db, acc, days)
    run = SyncRun(account_id=acc.id, date_from=d1, date_to=d2, triggered_by_user_id=user_id, status="running")
    db.add(run)
    db.commit()
    return run


def execute_run(run_id: int, http_factory: Callable[[], httpx.Client] = lambda: httpx.Client(timeout=60)) -> None:
    """Runs all steps for a created SyncRun. Safe to call from a background task or CLI."""
    with session_scope() as db, http_factory() as http:
        run = db.get(SyncRun, run_id)
        counts, errors = {}, {}
        try:
            acc = find_account(db, run.account_id)
            if acc is None:
                raise RuntimeError("Account is not active in P04")
            rs = open_read_session(db, acc.id, http)
        except Exception as e:  # noqa: BLE001 — recorded on the run
            errors["connect"] = getattr(e, "message", str(e))
            rs = None
        if rs is not None:
            for name, fn in STEPS:
                try:
                    counts[name] = fn(db, rs, acc, run.date_from, run.date_to)
                    db.commit()
                except Exception as e:  # noqa: BLE001
                    db.rollback()
                    errors[name] = getattr(e, "message", str(e))[:500]
                    log.warning("sync_step_failed", extra={"run_id": run_id, "step": name, "error": errors[name]})
        run = db.get(SyncRun, run_id)
        run.counts, run.errors = json.dumps(counts), json.dumps(errors)
        run.status = "success" if not errors else ("partial" if counts else "failed")
        run.finished_at = datetime.now(UTC)
        db.commit()
        log.info("sync_finished", extra={"run_id": run_id, "status": run.status, "counts": counts})
