"""P18 — run checks for an account, upsert alerts (dedupe per code, auto-resolve when cleared), acknowledge/resolve.
Change-impact monitoring starts once P17 executes approved changes (nothing is executed yet)."""
import json
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel.interface import list_websites
from app.modules.p05_ads_sync.interface import list_accounts, search_terms, summary
from app.modules.p06_analytics.interface import tracking_health
from app.modules.p18_monitoring import checks
from app.modules.p18_monitoring.models import Alert, MonitorCheck
from app.shared.errors import NotFoundError, ValidationFailed
from app.shared.feature_flags import is_enabled
from app.shared.logging import get_logger

MODULE_ID = "P18"
SCHEDULE_FLAG = "monitoring.scheduled.enabled"
OPEN = ("open", "acknowledged")
log = get_logger(MODULE_ID)


def _utc(v):
    return v.replace(tzinfo=UTC) if v is not None and v.tzinfo is None else v


def account(db: DbSession, account_id: int):
    acc = next((a for a in list_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or not active", module_id=MODULE_ID)
    return acc


def signals_for(db: DbSession, account_id: int, today: date) -> list[checks.Signal]:
    r1, r2, b1, _ = checks.windows(today)
    daily = summary(db, account_id, b1, r2)["daily"]
    recent = search_terms(db, account_id, r1, r2, limit=5000)
    new = [t for t in recent if t.get("first_seen") and t["first_seen"] >= r1.isoformat()]
    tracking = []
    for w in list_websites(db):
        if w.ads_account_id == account_id:
            try:
                tracking += tracking_health(db, w.id, today - timedelta(days=29), today)
            except Exception:  # noqa: BLE001 — one website's health must not stop the run
                log.warning("tracking_health_failed", extra={"website_id": w.id})
    seen, uniq = set(), []
    for h in tracking:
        if h["code"] not in seen:
            seen.add(h["code"])
            uniq.append(h)
    return checks.evaluate(daily, today, new_terms=new, recent_term_cost=sum(t["cost"] for t in recent), tracking=uniq)


def run(db: DbSession, account_id: int, *, trigger: str, by: str | None, today: date | None = None) -> MonitorCheck:
    account(db, account_id)
    run_row = MonitorCheck(account_id=account_id, trigger=trigger, run_by=by)
    db.add(run_row)
    db.commit()
    try:
        found = {s.code: s for s in signals_for(db, account_id, today or date.today())}
    except Exception as e:  # noqa: BLE001 — record the failure on the run
        run_row.status, run_row.error, run_row.finished_at = "failed", str(e)[:1000], datetime.now(UTC)
        db.commit()
        raise
    now = datetime.now(UTC)
    open_alerts = {a.code: a for a in db.scalars(select(Alert).where(Alert.account_id == account_id, Alert.status.in_(OPEN)))}
    opened = resolved = 0
    for code, s in found.items():
        a = open_alerts.get(code)
        if a:
            a.severity, a.title, a.detail, a.action, a.evidence, a.link = s.severity, s.title, s.detail, s.action, json.dumps(s.evidence), s.link
            a.last_seen_at, a.occurrences = now, a.occurrences + 1
        else:
            db.add(Alert(account_id=account_id, code=code, severity=s.severity, title=s.title, detail=s.detail, action=s.action,
                         evidence=json.dumps(s.evidence), link=s.link))
            opened += 1
    for code, a in open_alerts.items():
        if code not in found:
            a.status, a.resolved_at, a.resolved_by = "resolved", now, "auto"
            resolved += 1
    run_row.status, run_row.finished_at = "success", now
    run_row.signals, run_row.opened, run_row.resolved = len(found), opened, resolved
    db.commit()
    return run_row


def run_scheduled(db: DbSession) -> list[MonitorCheck]:
    """Entry point for Windows Task Scheduler / cron (see run.py). Does nothing unless the flag is on."""
    if not is_enabled(SCHEDULE_FLAG, db):
        log.info("scheduled_monitoring_disabled")
        return []
    out = []
    for a in list_accounts(db):
        try:
            out.append(run(db, a.id, trigger="scheduled", by="scheduler"))
        except Exception:  # noqa: BLE001 — one account failing must not stop the others
            log.exception("scheduled_run_failed", extra={"account_id": a.id})
    return out


def alerts(db: DbSession, account_id: int, status: str | None = None) -> list[Alert]:
    q = select(Alert).where(Alert.account_id == account_id)
    q = q.where(Alert.status == status) if status else q.where(Alert.status.in_(OPEN))
    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(db.scalars(q), key=lambda a: (order.get(a.severity, 9), -a.last_seen_at.timestamp() if a.last_seen_at else 0))


def set_status(db: DbSession, alert_id: int, status: str, *, by: str) -> Alert:
    a = db.get(Alert, alert_id)
    if a is None:
        raise NotFoundError("Alert not found", module_id=MODULE_ID)
    if status not in ("acknowledged", "resolved", "open"):
        raise ValidationFailed("status must be open, acknowledged or resolved", module_id=MODULE_ID)
    if status == "acknowledged":
        a.acknowledged_by = by
    if status == "resolved":
        a.resolved_at, a.resolved_by = datetime.now(UTC), by
    a.status = status
    db.commit()
    return a


def runs(db: DbSession, account_id: int, limit: int = 10) -> list[MonitorCheck]:
    return list(db.scalars(select(MonitorCheck).where(MonitorCheck.account_id == account_id).order_by(MonitorCheck.id.desc()).limit(limit)))


def alert_dict(a: Alert) -> dict:
    return {"id": a.id, "code": a.code, "severity": a.severity, "title": a.title, "detail": a.detail, "action": a.action,
            "evidence": json.loads(a.evidence), "link": a.link, "status": a.status, "occurrences": a.occurrences,
            "first_seen_at": _utc(a.first_seen_at), "last_seen_at": _utc(a.last_seen_at), "acknowledged_by": a.acknowledged_by,
            "resolved_at": _utc(a.resolved_at), "resolved_by": a.resolved_by}


def run_dict(r: MonitorCheck) -> dict:
    return {"id": r.id, "trigger": r.trigger, "status": r.status, "signals": r.signals, "opened": r.opened, "resolved": r.resolved,
            "error": r.error, "run_by": r.run_by, "started_at": _utc(r.started_at), "finished_at": _utc(r.finished_at)}
