"""P17 — runs APPROVED P16 changes against Google Ads, behind every guard the project has:

  validate  (no change at Google)  needs: execute permission, an approved P16 request, a buildable plan
  execute   (LIVE)                 needs ALL of: ADS_EXECUTION_KILL_SWITCH=false, flag ads.execution.enabled ON,
                                   execute permission, approval still 'approved', typed confirmation,
                                   and a successful validate of the IDENTICAL plan in the last 24 h
  rollback  (LIVE)                 same live guards + typed confirmation; removes exactly what an execution created

Nothing here runs by itself: every action is one explicit request from a signed-in user.
"""
import json
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.modules.p04_ads_connection.interface import AccountRef, active_accounts, open_api_credentials
from app.modules.p05_ads_sync.interface import campaigns
from app.modules.p09_ad_creative.interface import approved_drafts
from app.modules.p16_approvals.interface import approved_changes, get_approval, mark_executed
from app.modules.p17_ads_execution import google, plans
from app.modules.p17_ads_execution.models import Execution
from app.modules.p22_security_audit.interface import record as audit_record
from app.shared.config import get_settings
from app.shared.errors import NotFoundError, ValidationFailed
from app.shared.feature_flags import resolve
from app.shared.logging import get_logger

MODULE_ID = "P17"
CONFIRM_EXECUTE = "EXECUTE"
CONFIRM_ROLLBACK = "ROLLBACK"
VALIDATION_TTL = timedelta(hours=24)
SERVICE_FOR = {"add_negative_keywords": "campaignCriteria", "create_rsa": "adGroupAds"}
log = get_logger(MODULE_ID)


def _utc(v: datetime) -> datetime:
    return v if v.tzinfo else v.replace(tzinfo=UTC)


def status(db: DbSession) -> dict:
    s = resolve(google.FLAG, db)
    return {"kill_switch": get_settings().ads_execution_kill_switch, "flag_enabled": s.enabled, "flag_source": s.source,
            "live_execution_allowed": s.enabled, "supported_changes": list(plans.SUPPORTED)}


def _account(db: DbSession, account_id: int) -> AccountRef:
    acc = next((a for a in active_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or disabled", module_id=MODULE_ID)
    return acc


def _approved(db: DbSession, approval_id: int) -> dict:
    a = get_approval(db, approval_id)
    if a is None:
        raise NotFoundError("Approval not found", module_id=MODULE_ID)
    if a["status"] != "approved":
        raise ValidationFailed(f"Only approved requests can be sent to Google Ads (this one is '{a['status']}').", module_id=MODULE_ID)
    return a


def build_plan(db: DbSession, approval: dict) -> list[plans.Operation]:
    ct, acc = approval["change_type"], _account(db, approval["account_id"])
    try:
        if ct not in plans.SUPPORTED:
            raise plans.PlanError(f"'{ct}' can't be executed automatically yet — apply it by hand in Google Ads.")
        if ct == "add_negative_keywords":
            cams = campaigns(db, acc.id, datetime.now(UTC).date(), datetime.now(UTC).date())
            return plans.negatives_plan(acc.customer_id, approval["payload"].get("negatives", []), cams)
        draft = next((d for d in approved_drafts(db, acc.id) if d["id"] == approval["payload"].get("ad_draft_id")), None)
        if draft is None:
            raise plans.PlanError("The ad draft is no longer approved in Ads & Assets.")
        if draft.get("ad_group_name") != approval["payload"].get("ad_group_name"):
            raise plans.PlanError("The ad group on the draft changed after approval. Withdraw and re-approve it.")
        return plans.rsa_plan(acc.customer_id, approval["after"] | {"paths": approval["after"].get("paths", [])}, draft)
    except plans.PlanError as e:
        raise ValidationFailed(str(e), module_id=MODULE_ID) from e


def preview(db: DbSession, approval_id: int) -> dict:
    a = _approved(db, approval_id)
    ops = build_plan(db, a)
    return {"approval_id": a["id"], "title": a["title"], "change_type": a["change_type"], "plan_hash": plans.plan_hash(ops),
            "operations": [o.preview() for o in ops], "status": status(db)}


def changes(db: DbSession, account_id: int) -> list[dict]:
    """Approved changes with whether they can be executed here (and why not)."""
    _account(db, account_id)
    out = []
    for a in approved_changes(db, account_id):
        row = {"approval_id": a["id"], "title": a["title"], "change_type": a["change_type"], "impact": a["impact"],
               "risk": a["risk"], "decided_by": a["decided_by"], "executable": True, "reason": None, "plan_hash": None, "operations": []}
        try:
            ops = build_plan(db, a)
            row["plan_hash"], row["operations"] = plans.plan_hash(ops), [o.preview() for o in ops]
        except ValidationFailed as e:
            row["executable"], row["reason"] = False, e.message
        out.append(row)
    return out


def row_dict(r: Execution) -> dict:
    return {"id": r.id, "approval_id": r.approval_id, "account_id": r.account_id, "mode": r.mode, "status": r.status,
            "change_type": r.change_type, "plan_hash": r.plan_hash, "error": r.error, "resource_names": json.loads(r.resource_names),
            "rollback_of": r.rollback_of, "executed_by": r.executed_by, "created_at": r.created_at}


def history(db: DbSession, account_id: int, limit: int = 50) -> list[dict]:
    q = select(Execution).where(Execution.account_id == account_id).order_by(Execution.id.desc()).limit(limit)
    return [row_dict(r) for r in db.scalars(q)]


def _save(db, approval, mode, status_, ops, *, h, by, response=None, error=None, names=None, rollback_of=None) -> Execution:
    row = Execution(approval_id=approval["id"], account_id=approval["account_id"], mode=mode, status=status_,
                    change_type=approval["change_type"], plan_hash=h,
                    plan=json.dumps([{"service": o.service, "body": o.body(validate_only=(mode == "validate"))} for o in ops]),
                    response=json.dumps(response)[:8000] if response is not None else None, error=error,
                    resource_names=json.dumps(names or []), rollback_of=rollback_of, executed_by=by)
    db.add(row)
    audit_record(db, module_id=MODULE_ID, action=f"execution_{mode}_{status_}", actor=by, entity_type="approval",
                 entity_id=approval["id"], before={"approval_status": approval["status"]},
                 after={"mode": mode, "status": status_, "plan_hash": h, "resources": names or [], "error": error}, commit=False)
    db.commit()
    return row


def _call(db, creds, op, *, validate_only):
    """One Google request. Rejections raise ExecutionFailed (Google did NOT apply it); transport errors raise
    UnknownOutcome (the request may or may not have been applied — never assume either)."""
    try:
        return google.send(db, creds, op, validate_only=validate_only)
    except httpx.HTTPError as e:
        raise UnknownOutcome(f"No answer from Google Ads ({type(e).__name__}) — the change may or may not have been applied. "
                             "Check the account in Google Ads before doing anything else.", module_id=MODULE_ID) from e


class UnknownOutcome(google.ExecutionFailed):
    code = "execution_outcome_unknown"


def _one_op(ops):
    if len(ops) != 1:
        raise ValidationFailed("Multi-step plans aren't supported yet.", module_id=MODULE_ID)
    return ops[0]


def validate(db: DbSession, approval_id: int, *, by: str, http: httpx.Client | None = None) -> dict:
    """Ask Google to check the request without applying it. Safe: Google guarantees validateOnly changes nothing."""
    a = _approved(db, approval_id)
    ops = build_plan(db, a)
    h = plans.plan_hash(ops)
    op = _one_op(ops)
    with (http or httpx.Client()) as client:
        creds = open_api_credentials(db, a["account_id"], client)
        try:
            resp = _call(db, creds, op, validate_only=True)
        except google.ExecutionFailed as e:
            _save(db, a, "validate", "failed", ops, h=h, by=by, error=e.message)
            raise
    return row_dict(_save(db, a, "validate", "validated", ops, h=h, by=by, response=resp))


def _has_fresh_validation(db: DbSession, approval_id: int, h: str) -> bool:
    cutoff = datetime.now(UTC) - VALIDATION_TTL
    rows = db.scalars(select(Execution).where(Execution.approval_id == approval_id, Execution.mode == "validate",
                                              Execution.status == "validated", Execution.plan_hash == h))
    return any(_utc(r.created_at) >= cutoff for r in rows)


def _claim_execute(db, approval, ops, h, by) -> Execution:
    """Reserve the approval BEFORE talking to Google. A unique partial index allows at most one pending/executed/unknown
    execute row per approval, so a double click, a retry after a crash, or two tabs can never send the change twice."""
    row = Execution(approval_id=approval["id"], account_id=approval["account_id"], mode="execute", status="pending",
                    change_type=approval["change_type"], plan_hash=h,
                    plan=json.dumps([{"service": o.service, "body": o.body(validate_only=False)} for o in ops]), executed_by=by)
    db.add(row)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValidationFailed("This change was already executed, is executing right now, or its outcome is unknown — "
                               "check Google Ads and the history below; it will not be sent again automatically.",
                               module_id=MODULE_ID) from e
    return row


def _finish(db, row, approval, status_, *, resp=None, names=None, error=None) -> Execution:
    row.status, row.error = status_, error
    row.response = json.dumps(resp)[:8000] if resp is not None else None
    row.resource_names = json.dumps(names or [])
    audit_record(db, module_id=MODULE_ID, action=f"execution_execute_{status_}", actor=row.executed_by, entity_type="approval",
                 entity_id=approval["id"], before={"approval_status": approval["status"]},
                 after={"mode": "execute", "status": status_, "plan_hash": row.plan_hash, "resources": names or [], "error": error},
                 commit=False)
    db.commit()
    return row


def execute(db: DbSession, approval_id: int, *, by: str, confirm: str | None, http: httpx.Client | None = None) -> dict:
    google.assert_live_allowed(db)                                     # kill switch + flag, before anything else
    if (confirm or "").strip() != CONFIRM_EXECUTE:
        raise ValidationFailed(f"Type {CONFIRM_EXECUTE} to confirm a live change to Google Ads.", module_id=MODULE_ID,
                               details={"confirm_required": CONFIRM_EXECUTE})
    a = _approved(db, approval_id)
    ops = build_plan(db, a)
    h = plans.plan_hash(ops)
    op = _one_op(ops)
    if not _has_fresh_validation(db, approval_id, h):
        raise ValidationFailed("Validate this exact change with Google first (valid for 24 h), then execute.", module_id=MODULE_ID)
    row = _claim_execute(db, a, ops, h, by)
    try:
        with (http or httpx.Client()) as client:
            creds = open_api_credentials(db, a["account_id"], client)
            resp = _call(db, creds, op, validate_only=False)
    except UnknownOutcome as e:
        _finish(db, row, a, "unknown", error=e.message)         # stays claimed: blocks any automatic re-send
        raise
    except Exception as e:                                       # Google rejected it / we never sent it: safe to retry later
        _finish(db, row, a, "failed", error=getattr(e, "message", str(e))[:500])
        raise
    names = google.resource_names(resp)
    _finish(db, row, a, "executed", resp=resp, names=names)
    note = "OK" if names else "OK (Google returned no resource names — rollback unavailable)"
    try:
        mark_executed(db, approval_id, result=f"{op.label}: {note}", by=by)
    except Exception:  # Google already applied it — never hide that; the claimed row above is the record and blocks a re-send
        log.exception("p16_mark_executed_failed", extra={"approval_id": approval_id})
    return row_dict(row)


def rollback(db: DbSession, execution_id: int, *, by: str, confirm: str | None, http: httpx.Client | None = None) -> dict:
    google.assert_live_allowed(db)
    if (confirm or "").strip() != CONFIRM_ROLLBACK:
        raise ValidationFailed(f"Type {CONFIRM_ROLLBACK} to confirm removing what was created.", module_id=MODULE_ID,
                               details={"confirm_required": CONFIRM_ROLLBACK})
    orig = db.get(Execution, execution_id)
    if orig is None or orig.mode != "execute":
        raise NotFoundError("Execution not found", module_id=MODULE_ID)
    acc = _account(db, orig.account_id)
    names = json.loads(orig.resource_names)
    if any(not n.startswith(f"customers/{acc.customer_id}/") for n in names):
        raise ValidationFailed("Stored resource names don't belong to this account — refusing to roll back.", module_id=MODULE_ID)
    try:
        ops = plans.rollback_plan(SERVICE_FOR[orig.change_type], names)
    except plans.PlanError as e:
        raise ValidationFailed(str(e), module_id=MODULE_ID) from e
    claimed = db.execute(update(Execution).where(Execution.id == orig.id, Execution.status == "executed")
                         .values(status="rolling_back")).rowcount
    db.commit()
    if claimed != 1:
        db.refresh(orig)
        raise ValidationFailed(f"This execution is '{orig.status}' — only an executed change can be rolled back, once.", module_id=MODULE_ID)
    approval = {"id": orig.approval_id, "account_id": orig.account_id, "change_type": orig.change_type, "status": "executed"}
    h = plans.plan_hash(ops)
    try:
        with (http or httpx.Client()) as client:
            creds = open_api_credentials(db, orig.account_id, client)
            resp = _call(db, creds, ops[0], validate_only=False)
    except UnknownOutcome as e:
        db.execute(update(Execution).where(Execution.id == orig.id).values(status="unknown", error="rollback: " + e.message[:400]))
        db.commit()
        raise
    except Exception:                                            # rejected / never sent: the execution is still rollback-able
        db.execute(update(Execution).where(Execution.id == orig.id).values(status="executed"))
        db.commit()
        raise
    db.execute(update(Execution).where(Execution.id == orig.id).values(status="rolled_back"))
    return row_dict(_save(db, approval, "rollback", "rolled_back", ops, h=h, by=by, response=resp, names=names, rollback_of=orig.id))
