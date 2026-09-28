"""P14 — recommendation store: ingest P07 audit issues, prioritise, track decisions, AI action plan."""
import json
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p05_ads_sync.interface import list_accounts, summary
from app.modules.p07_ppc_audit.interface import latest_audit
from app.modules.p14_recommendations import ai
from app.modules.p14_recommendations.models import AIEvidence, AIRun, Recommendation
from app.modules.p21_business_rules.interface import get_rules
from app.shared.errors import NotFoundError, ValidationFailed
from app.shared.feature_flags import resolve
from app.shared.logging import get_logger

MODULE_ID = "P14"
AI_FLAG = "ai.live_calls.enabled"
# Changes made inside Google Ads need an approval record (P16) before P17 may ever execute them.
GOOGLE_ADS_CATEGORIES = {"account", "bidding", "keywords", "search_terms", "ads"}
TRANSITIONS = {"proposed": {"accepted", "rejected"}, "accepted": {"done", "proposed"}, "rejected": {"proposed"},
               "done": {"accepted"}, "superseded": {"proposed"}}
log = get_logger(MODULE_ID)


def account(db: DbSession, account_id: int):
    acc = next((a for a in list_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or not active", module_id=MODULE_ID)
    return acc


def priority(severity: str, confidence: float, risk: str) -> int:
    return {"critical": 300, "warning": 200, "info": 100}[severity] + round(confidence * 100) \
        - {"low": 0, "medium": 20, "high": 50}.get(risk, 0)


def refresh(db: DbSession, account_id: int) -> dict:
    """Upsert recommendations from the latest P07 audit. Proposals the audit no longer reports → superseded."""
    account(db, account_id)
    audit = latest_audit(db, account_id)
    if audit is None:
        raise ValidationFailed("Run an account audit first (Audit page)", module_id=MODULE_ID)
    existing = {r.source_ref: r for r in db.scalars(select(Recommendation).where(Recommendation.ads_account_id == account_id))}
    seen, created = set(), 0
    for i in audit["issues"]:
        ref = f"P07|{i['code']}|{i['entity_type']}|{i['entity_id']}"[:600]
        seen.add(ref)
        r = existing.get(ref)
        if r is None:
            r = Recommendation(module_id="P07", source_ref=ref, ads_account_id=account_id, status="proposed")
            db.add(r)
            created += 1
        elif r.status == "superseded":
            r.status = "proposed"
        r.entity_type, r.entity_id, r.category, r.severity = i["entity_type"], i["entity_id"], i["category"], i["severity"]
        r.title, r.observation, r.evidence = i["title"], i["observation"], json.dumps(i["evidence"])
        r.reasoning, r.proposed_action, r.expected_impact = i["reasoning"], i["proposed_action"], i["expected_impact"]
        r.confidence, r.risk = i["confidence"], i["risk"]
        r.priority = priority(i["severity"], i["confidence"], i["risk"])
        r.requires_approval = i["category"] in GOOGLE_ADS_CATEGORIES
        r.link = i.get("link")
    superseded = 0
    for ref, r in existing.items():
        if ref not in seen and r.status == "proposed":
            r.status, superseded = "superseded", superseded + 1
    db.commit()
    return {"from_audit": audit["created_at"], "total": len(audit["issues"]), "new": created, "superseded": superseded}


def list_recs(db: DbSession, account_id: int, status: str | None = None) -> list[Recommendation]:
    q = select(Recommendation).where(Recommendation.ads_account_id == account_id)
    q = q.where(Recommendation.status == status) if status else q.where(Recommendation.status != "superseded")
    return list(db.scalars(q.order_by(Recommendation.priority.desc(), Recommendation.id)))


def set_status(db: DbSession, rec_id: int, status: str, *, by: str, note: str | None) -> Recommendation:
    r = db.get(Recommendation, rec_id)
    if r is None:
        raise NotFoundError("Recommendation not found", module_id=MODULE_ID)
    if status not in TRANSITIONS.get(r.status, set()):
        raise ValidationFailed(f"Cannot move from '{r.status}' to '{status}'", module_id=MODULE_ID)
    now = datetime.now(UTC)
    r.status, r.decided_by, r.decision_note = status, by, note
    if status == "accepted":
        r.approved_at = now
    if status == "done":
        r.executed_at, r.execution_result = now, "marked done manually"
    db.commit()
    return r


def rec_dict(r: Recommendation) -> dict:
    return {"id": r.id, "module_id": r.module_id, "website_id": r.website_id, "ads_account_id": r.ads_account_id,
            "entity_type": r.entity_type, "entity_id": r.entity_id, "category": r.category, "severity": r.severity,
            "priority": r.priority, "title": r.title, "observation": r.observation, "evidence": json.loads(r.evidence),
            "reasoning": r.reasoning, "proposed_action": r.proposed_action, "expected_impact": r.expected_impact,
            "confidence": r.confidence, "risk": r.risk, "assumptions": json.loads(r.assumptions),
            "requires_approval": r.requires_approval, "link": r.link, "status": r.status, "decided_by": r.decided_by,
            "decision_note": r.decision_note, "created_at": r.created_at, "approved_at": r.approved_at,
            "executed_at": r.executed_at, "execution_result": r.execution_result}


# ---- AI action plan ------------------------------------------------------------------------

def ai_status(db: DbSession) -> dict:
    flag = resolve(AI_FLAG, db)
    key = bool(ai.P14Settings().anthropic_api_key)
    return {"flag_enabled": flag.enabled, "api_key_configured": key, "live": flag.enabled and key,
            "model": ai.P14Settings().ai_model}


def generate_plan(db: DbSession, account_id: int, *, by: str) -> AIRun:
    acc = account(db, account_id)
    recs = [rec_dict(r) for r in list_recs(db, account_id) if r.status in ("proposed", "accepted")]
    if not recs:
        raise ValidationFailed("No open recommendations — run an audit and refresh first", module_id=MODULE_ID)
    d2 = date.today()
    totals = summary(db, account_id, d2 - timedelta(days=89), d2)["totals"]
    rules = get_rules(db, account_id)
    snapshot = {"account": acc.descriptive_name or acc.customer_id, "currency": acc.currency_code or "AUD",
                "last_90_days": totals, "services": rules.services[:15], "areas": rules.locations[:15],
                "target_cost_per_conversion": rules.target_cost_per_conversion}
    brief = [{k: r[k] for k in ("id", "severity", "category", "title", "observation", "evidence", "reasoning",
                                "proposed_action", "confidence", "requires_approval", "status")} for r in recs[:25]]
    st = ai_status(db)
    run = AIRun(ads_account_id=account_id, kind="action_plan", mode="live" if st["live"] else "template",
                model=st["model"] if st["live"] else None, created_by=by, status="failed")
    try:
        if st["live"]:
            plan, tin, tout, model = ai.call_claude(ai.build_prompt(snapshot, brief), ai.P14Settings())
            run.input_tokens, run.output_tokens, run.model = tin, tout, model
        else:
            plan = ai.template_plan(snapshot, recs)
        known = {r["id"] for r in brief}
        for a in plan.top_actions:  # drop hallucinated ids
            a.recommendation_ids = [i for i in a.recommendation_ids if i in known]
        plan.thirty_day_plan = [w for w in plan.thirty_day_plan if w.focus.strip() and w.tasks]  # drop empty weeks
        run.output, run.status = plan.model_dump_json(), "success"
    except ai.AIError as e:
        run.error = str(e)
    db.add(run)
    db.flush()
    db.add_all(AIEvidence(run_id=run.id, recommendation_id=r["id"]) for r in brief)
    db.commit()
    log.info("ai_plan", extra={"run_id": run.id, "mode": run.mode, "status": run.status, "tokens_out": run.output_tokens})
    return run


def latest_plan(db: DbSession, account_id: int) -> AIRun | None:
    return db.scalars(select(AIRun).where(AIRun.ads_account_id == account_id, AIRun.kind == "action_plan")
                      .order_by(AIRun.id.desc()).limit(1)).first()
