"""P12 — runs the read-only segment pull, analyses it, and keeps the latest snapshot + findings per account."""
import json
from datetime import UTC, date, datetime, timedelta

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.modules.p04_ads_connection.interface import AccountRef, active_accounts, open_read_session
from app.modules.p12_budget_bid import analysis, gaql
from app.modules.p12_budget_bid.models import SegmentFinding, SegmentRun
from app.modules.p21_business_rules.interface import get_rules
from app.shared.errors import AppError, NotFoundError
from app.shared.logging import get_logger

MODULE_ID = "P12"
KEEP_RUNS = 10
TOP_LOCATIONS = 40
log = get_logger(MODULE_ID)


class PullFailed(AppError):
    status_code = 502
    code = "google_ads_read_failed"


def account(db: DbSession, account_id: int) -> AccountRef:
    acc = next((a for a in active_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or disabled", module_id=MODULE_ID)
    return acc


def run(db: DbSession, account_id: int, days: int, *, by: str | None, http: httpx.Client | None = None) -> dict:
    account(db, account_id)
    d2 = date.today()
    d1 = d2 - timedelta(days=days - 1)
    try:
        with (http or httpx.Client(timeout=90)) as client:
            data = gaql.pull(open_read_session(db, account_id, client), d1, d2)
    except AppError:
        raise
    except Exception as e:  # the Google Ads read failed — keep a record, tell the user plainly
        db.add(SegmentRun(account_id=account_id, days=days, date_from=d1, date_to=d2, status="failed", error=str(e)[:500], created_by=by))
        db.commit()
        raise PullFailed(f"Could not read segment data from Google Ads: {str(e)[:200]}", module_id=MODULE_ID) from e
    rules = get_rules(db, account_id)
    findings, meta = analysis.analyse(data, target_cpa=rules.target_cost_per_conversion, not_served=rules.other_locations)
    payload = {"tables": {"device": data["device"], "day": data["day"], "daypart": meta["dayparts"], "hour": data["hour"],
                          "location": data["location"][:TOP_LOCATIONS], "campaigns": data["campaigns"]},
               "total": meta["total"], "average_cpa": meta["average_cpa"], "target_cpa": rules.target_cost_per_conversion}
    row = SegmentRun(account_id=account_id, days=days, date_from=d1, date_to=d2, status="success", payload=json.dumps(payload), created_by=by)
    db.add(row)
    db.flush()
    for f in findings:
        db.add(SegmentFinding(run_id=row.id, account_id=account_id, dimension=f.dimension, segment=f.segment[:255], code=f.code,
                              severity=f.severity, title=f.title, observation=f.observation, evidence=json.dumps(f.evidence),
                              proposed_action=f.proposed_action, confidence=f.confidence))
    old = db.scalars(select(SegmentRun.id).where(SegmentRun.account_id == account_id).order_by(SegmentRun.id.desc()).offset(KEEP_RUNS)).all()
    if old:
        db.execute(delete(SegmentFinding).where(SegmentFinding.run_id.in_(old)))
        db.execute(delete(SegmentRun).where(SegmentRun.id.in_(old)))
    db.commit()
    log.info("segment_run_done", extra={"account_id": account_id, "findings": len(findings)})
    return latest(db, account_id)


def _run_dict(r: SegmentRun) -> dict:
    return {"id": r.id, "days": r.days, "date_from": r.date_from, "date_to": r.date_to, "status": r.status, "error": r.error,
            "created_by": r.created_by, "created_at": r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=UTC)}


def latest(db: DbSession, account_id: int) -> dict | None:
    r = db.scalar(select(SegmentRun).where(SegmentRun.account_id == account_id, SegmentRun.status == "success").order_by(SegmentRun.id.desc()))
    if r is None:
        return None
    fs = db.scalars(select(SegmentFinding).where(SegmentFinding.run_id == r.id).order_by(SegmentFinding.id)).all()
    payload = json.loads(r.payload)
    return {"run": _run_dict(r), "total": payload["total"], "average_cpa": payload["average_cpa"], "target_cpa": payload["target_cpa"],
            "tables": payload["tables"],
            "findings": [{"id": f.id, "dimension": f.dimension, "segment": f.segment, "code": f.code, "severity": f.severity, "title": f.title,
                          "observation": f.observation, "evidence": json.loads(f.evidence), "proposed_action": f.proposed_action,
                          "confidence": f.confidence} for f in fs]}


def last_run(db: DbSession, account_id: int) -> dict | None:
    r = db.scalar(select(SegmentRun).where(SegmentRun.account_id == account_id).order_by(SegmentRun.id.desc()))
    return _run_dict(r) if r else None
