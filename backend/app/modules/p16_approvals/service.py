"""P16 — the approval queue. Collects proposed Google Ads changes from P08/P09/P14/P15 (and direct requests from other
modules), records decisions with before/after + evidence, and is the only source P17 may execute from."""
import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p08_keyword_intel.interface import accepted_negatives
from app.modules.p09_ad_creative.interface import approved_drafts
from app.modules.p14_recommendations.interface import open_recommendations
from app.modules.p15_campaign_builder.interface import approved_campaign_drafts
from app.modules.p16_approvals.models import Approval, ApprovalEvent
from app.shared.errors import NotFoundError, PermissionDenied, ValidationFailed
from app.shared.logging import get_logger

MODULE_ID = "P16"
CONFIRM_PHRASE = "APPROVE"
HIGH_IMPACT = {"create_campaign", "bidding_change", "enable_campaigns", "budget_change_major", "structure_change"}
REC_CHANGE = {"bidding": "bidding_change", "account": "enable_campaigns", "keywords": "keyword_change",
              "search_terms": "add_negative_keywords", "ads": "ad_change"}
log = get_logger(MODULE_ID)


def _event(db: DbSession, a: Approval, event: str, by: str | None, note: str | None = None) -> None:
    db.add(ApprovalEvent(approval_id=a.id, event=event, by=by, note=note))


def request_approval(db: DbSession, *, account_id: int, source_module: str, source_ref: str, change_type: str, title: str,
                     before: dict, after: dict, evidence: list, risk: str, payload: dict, requested_by: str | None) -> Approval:
    """Idempotent by (account, source_ref) while a request is open (pending/approved)."""
    open_ = db.scalar(select(Approval).where(Approval.account_id == account_id, Approval.source_ref == source_ref,
                                             Approval.status.in_(["pending", "approved"])))
    if open_:
        return open_
    a = Approval(account_id=account_id, source_module=source_module, source_ref=source_ref[:255], change_type=change_type,
                 impact="high" if change_type in HIGH_IMPACT else "standard", risk=risk if risk in ("low", "medium", "high") else "medium",
                 title=title[:2000], before=json.dumps(before, default=str), after=json.dumps(after, default=str),
                 evidence=json.dumps(evidence, default=str), payload=json.dumps(payload, default=str), requested_by=requested_by)
    db.add(a)
    db.flush()
    _event(db, a, "requested", requested_by)
    return a


def sync_queue(db: DbSession, account_id: int, *, by: str) -> dict:
    """Pull approval-worthy items from source modules; withdraw requests whose source is no longer approved."""
    created, live_refs = 0, set()

    def req(**kw):
        nonlocal created
        live_refs.add(kw["source_ref"])
        before_n = db.scalar(select(Approval.id).where(Approval.account_id == account_id, Approval.source_ref == kw["source_ref"],
                                                       Approval.status.in_(["pending", "approved"])))
        request_approval(db, account_id=account_id, requested_by=by, **kw)
        created += 0 if before_n else 1

    for r in open_recommendations(db, account_id):
        if r["requires_approval"] and r["status"] == "accepted":
            req(source_module="P14", source_ref=f"P14|rec|{r['id']}", change_type=REC_CHANGE.get(r["category"], "other_change"),
                title=r["title"], before={"now": r["observation"]}, after={"proposed": r["proposed_action"]},
                evidence=r["evidence"], risk=r["risk"], payload={"recommendation_id": r["id"], "category": r["category"],
                                                                 "entity_type": r["entity_type"], "entity_id": r["entity_id"]})
    negs = accepted_negatives(db, account_id)
    covered = {i for a in db.scalars(select(Approval).where(Approval.account_id == account_id, Approval.change_type == "add_negative_keywords",
                                                            Approval.source_module == "P08", Approval.status != "withdrawn"))
               for i in json.loads(a.payload).get("negative_ids", [])}
    new = [n for n in negs if n["id"] not in covered]
    if new:
        ids = sorted(n["id"] for n in new)
        req(source_module="P08", source_ref="P08|negatives|" + hashlib.sha1(",".join(map(str, ids)).encode()).hexdigest()[:16],
            change_type="add_negative_keywords", title=f"Add {len(new)} negative keyword(s)",
            before={"negatives": "not in the account"},
            after={"negatives": [f'"{n["text"]}"' if n["match_type"] == "PHRASE" else f"[{n['text']}]" for n in new]},
            evidence=[[n["text"], f"AUD {n['cost']} wasted, {n['clicks']} clicks, {n['conversions']} conv."] for n in new[:20]],
            risk="low", payload={"negative_ids": ids, "negatives": [{"text": n["text"], "match_type": n["match_type"],
                                                                      "level": n["level"], "campaign_id": n["campaign_google_id"]} for n in new]})
    live_refs |= {a.source_ref for a in db.scalars(select(Approval).where(Approval.account_id == account_id, Approval.source_module == "P08"))}
    for d in approved_drafts(db, account_id):
        req(source_module="P09", source_ref=f"P09|ad|{d['id']}", change_type="create_rsa",
            title=f"Add responsive search ad to '{d['ad_group_name']}'", before={"ad": "none"},
            after={"headlines": d["headlines"], "descriptions": d["descriptions"], "final_url": d["final_url"],
                   "paths": [d["path1"], d["path2"]]},
            evidence=[["Strength (estimate)", str(d["strength"])], ["Written by", d["mode"] + (f" ({d['model']})" if d["model"] else "")]],
            risk="low", payload={"ad_draft_id": d["id"], "campaign_name": d["campaign_name"], "ad_group_name": d["ad_group_name"]})
    for c in approved_campaign_drafts(db, account_id):
        s = c["settings"]
        req(source_module="P15", source_ref=f"P15|campaign|{c['id']}", change_type="create_campaign",
            title=f"Create paused campaign '{c['name']}'", before={"campaign": "does not exist"},
            after={"ad_groups": [f"{g['name']} ({len(g['keywords'])} keywords)" for g in c["ad_groups"]],
                   "negatives": len(c["negatives"]), "budget": f"AUD {s['daily_budget']}/day",
                   "bidding": s["bidding"], "status": "PAUSED"},
            evidence=[[i["label"], i["status"]] for i in c["checklist"]], risk="medium", payload={"campaign_draft_id": c["id"]})
    withdrawn = 0
    for a in db.scalars(select(Approval).where(Approval.account_id == account_id, Approval.status.in_(["pending", "approved"]))):
        if a.source_ref not in live_refs and a.source_module in ("P09", "P14", "P15"):
            a.status, withdrawn = "withdrawn", withdrawn + 1
            _event(db, a, "withdrawn", "system", "source is no longer approved/accepted in its module")
    db.commit()
    return {"created": created, "withdrawn": withdrawn}


def get(db: DbSession, approval_id: int) -> Approval:
    a = db.get(Approval, approval_id)
    if a is None:
        raise NotFoundError("Approval not found", module_id=MODULE_ID)
    return a


def decide(db: DbSession, approval_id: int, decision: str, *, by: str, note: str | None, confirm: str | None) -> Approval:
    a = get(db, approval_id)
    if decision not in ("approve", "reject", "withdraw"):
        raise ValidationFailed("decision must be approve, reject or withdraw", module_id=MODULE_ID)
    allowed = {"approve": {"pending"}, "reject": {"pending"}, "withdraw": {"pending", "approved"}}[decision]
    if a.status not in allowed:
        raise ValidationFailed(f"Cannot {decision} a request that is '{a.status}'", module_id=MODULE_ID)
    if decision == "approve":
        if a.impact == "high" and (confirm or "").strip() != CONFIRM_PHRASE:
            raise ValidationFailed(f"High-impact change: type {CONFIRM_PHRASE} to confirm", module_id=MODULE_ID,
                                   details={"confirm_required": CONFIRM_PHRASE})
        if a.requested_by and a.requested_by == by and a.impact == "high" and not note:
            raise PermissionDenied("Approving your own high-impact request needs a note explaining why", module_id=MODULE_ID)
    if decision == "reject" and not (note or "").strip():
        raise ValidationFailed("Please give a reason when rejecting", module_id=MODULE_ID)
    a.status = {"approve": "approved", "reject": "rejected", "withdraw": "withdrawn"}[decision]
    a.decided_by, a.decided_at, a.decision_note = by, datetime.now(UTC), note
    _event(db, a, a.status, by, note)
    db.commit()
    log.info("approval_decided", extra={"approval_id": a.id, "status": a.status, "by": by, "impact": a.impact})
    return a


def mark_executed(db: DbSession, approval_id: int, *, result: str, by: str) -> Approval:
    a = get(db, approval_id)
    if a.status != "approved":
        raise ValidationFailed("Only approved requests can be executed", module_id=MODULE_ID)
    a.status, a.executed_at, a.execution_result = "executed", datetime.now(UTC), result[:4000]
    _event(db, a, "executed", by, result[:500])
    db.commit()
    return a


def list_approvals(db: DbSession, account_id: int, status: str | None) -> list[Approval]:
    q = select(Approval).where(Approval.account_id == account_id)
    if status:
        q = q.where(Approval.status == status)
    return list(db.scalars(q.order_by(Approval.id.desc())))


def history(db: DbSession, approval_id: int) -> list[ApprovalEvent]:
    return list(db.scalars(select(ApprovalEvent).where(ApprovalEvent.approval_id == approval_id).order_by(ApprovalEvent.id)))


def approval_dict(db: DbSession, a: Approval, with_history: bool = False) -> dict:
    d = {"id": a.id, "account_id": a.account_id, "source_module": a.source_module, "source_ref": a.source_ref,
         "change_type": a.change_type, "impact": a.impact, "risk": a.risk, "title": a.title, "before": json.loads(a.before),
         "after": json.loads(a.after), "evidence": json.loads(a.evidence), "payload": json.loads(a.payload), "status": a.status,
         "requested_by": a.requested_by, "decided_by": a.decided_by, "decided_at": a.decided_at, "decision_note": a.decision_note,
         "executed_at": a.executed_at, "execution_result": a.execution_result, "created_at": a.created_at,
         "confirm_required": CONFIRM_PHRASE if a.impact == "high" else None}
    if with_history:
        d["history"] = [{"event": e.event, "by": e.by, "note": e.note, "at": e.at} for e in history(db, a.id)]
    return d
