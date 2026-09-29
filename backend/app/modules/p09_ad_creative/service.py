"""P09 — existing-ad analysis, AI/template ad drafts, checks, review and export."""
import csv
import io
import json
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.modules.p05_ads_sync.interface import ad_groups, ads, keywords, list_accounts
from app.modules.p09_ad_creative import writer
from app.modules.p09_ad_creative.checks import check_ad, strength
from app.modules.p09_ad_creative.models import AdDraft, ClaimCheck
from app.modules.p21_business_rules.interface import get_rules
from app.modules.p22_security_audit.interface import record as audit_record
from app.shared.errors import AppError, NotFoundError, ValidationFailed
from app.shared.feature_flags import is_enabled
from app.shared.logging import get_logger

MODULE_ID = "P09"
AI_FLAG = "ai.live_calls.enabled"  # declared by P14; read-only here
log = get_logger(MODULE_ID)


class AIFailed(AppError):
    status_code = 502
    code = "ai_failed"


def account(db: DbSession, account_id: int):
    acc = next((a for a in list_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or not active", module_id=MODULE_ID)
    return acc


def _window(days: int) -> tuple[date, date]:
    d2 = date.today()
    return d2 - timedelta(days=days - 1), d2


def _kw_by_group(db: DbSession, account_id: int, d1: date, d2: date) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for k in keywords(db, account_id, d1, d2):
        if k.get("status") == "ENABLED":
            out[k["ad_group_google_id"]].append(k)
    for v in out.values():
        v.sort(key=lambda k: (-k["impressions"], -k["clicks"]))
    return out


def analyse_existing(db: DbSession, account_id: int, days: int) -> list[dict]:
    account(db, account_id)
    d1, d2 = _window(days)
    rules = get_rules(db, account_id)
    groups = {g["google_id"]: g for g in ad_groups(db, account_id, d1, d2)}
    name_to_id = {g["name"]: gid for gid, g in groups.items()}
    kws = _kw_by_group(db, account_id, d1, d2)
    out = []
    for a in ads(db, account_id, d1, d2):
        if a.get("type") != "RESPONSIVE_SEARCH_AD" or a.get("status") == "REMOVED":
            continue
        gid = name_to_id.get(a["ad_group_name"])
        top = [k["text"] for k in kws.get(gid, [])[:10]]
        f = check_ad(a["headlines"], a["descriptions"], [], keywords=top, locations=rules.locations,
                     approved_claims=[], competitors=rules.competitor_terms)
        out.append({"key": a["key"], "ad_id": a["ad_id"], "status": a["status"], "campaign_name": a["campaign_name"],
                    "ad_group_name": a["ad_group_name"], "ad_group_google_id": gid, "final_urls": a["final_urls"],
                    "headlines": a["headlines"], "descriptions": a["descriptions"],
                    "strength": strength(a["headlines"], a["descriptions"], f),
                    "findings": [x.__dict__ for x in f], "cost": a["cost"], "clicks": a["clicks"],
                    "impressions": a["impressions"], "ctr": a["ctr"], "conversions": a["conversions"]})
    return sorted(out, key=lambda r: (r["strength"], -r["cost"]))


def ad_group_options(db: DbSession, account_id: int, days: int) -> list[dict]:
    account(db, account_id)
    d1, d2 = _window(days)
    kws = _kw_by_group(db, account_id, d1, d2)
    urls: dict[str, str] = {}
    for a in ads(db, account_id, d1, d2):
        if a["final_urls"]:
            urls.setdefault(a["ad_group_name"], a["final_urls"][0])
    return [{"google_id": g["google_id"], "name": g["name"], "campaign_name": g["campaign_name"], "status": g["status"],
             "keywords": [k["text"] for k in kws.get(g["google_id"], [])[:25]], "keyword_count": len(kws.get(g["google_id"], [])),
             "final_url": urls.get(g["name"], "")} for g in ad_groups(db, account_id, d1, d2)]


def _apply_checks(db: DbSession, d: AdDraft) -> None:
    rules = get_rules(db, d.account_id)
    usps = json.loads(d.usps)
    f = check_ad(json.loads(d.headlines), json.loads(d.descriptions), [d.path1, d.path2], keywords=json.loads(d.keywords),
                 locations=rules.locations, approved_claims=usps, competitors=rules.competitor_terms)
    db.execute(delete(ClaimCheck).where(ClaimCheck.draft_id == d.id))
    db.add_all(ClaimCheck(draft_id=d.id, **x.__dict__) for x in f)
    d.strength = strength(json.loads(d.headlines), json.loads(d.descriptions), f)


def ai_live(db: DbSession) -> bool:
    return is_enabled(AI_FLAG, db) and bool(writer.P09Settings().anthropic_api_key)


def create_draft(db: DbSession, account_id: int, *, ad_group_name: str, campaign_name: str, ad_group_google_id: str | None,
                 final_url: str, kw: list[str], usps: list[str], use_ai: bool, by: str) -> AdDraft:
    account(db, account_id)
    if not ad_group_name.strip():
        raise ValidationFailed("Ad group name is required", module_id=MODULE_ID)
    rules = get_rules(db, account_id)
    brand = rules.brand_terms[0] if rules.brand_terms else None
    existing = []
    if ad_group_google_id:
        d1, d2 = _window(90)
        existing = [h for a in ads(db, account_id, d1, d2) if a["ad_group_name"] == ad_group_name for h in a["headlines"]]
    d = AdDraft(account_id=account_id, ad_group_name=ad_group_name.strip()[:255], campaign_name=campaign_name[:255],
                ad_group_google_id=ad_group_google_id, final_url=final_url.strip()[:1024], keywords=json.dumps(kw[:50]),
                usps=json.dumps([u.strip() for u in usps if u.strip()][:20]), created_by=by, mode="template")
    if use_ai and ai_live(db):
        brief = writer.brief_text(d.ad_group_name, kw, d.final_url, rules.services, rules.locations, json.loads(d.usps), brand, existing)
        try:
            copy, tin, tout, model = writer.write_with_claude(brief, writer.P09Settings())
        except writer.WriterError as e:
            raise AIFailed(str(e), module_id=MODULE_ID) from e
        d.mode, d.model, d.input_tokens, d.output_tokens = "live", model, tin, tout
    else:
        copy = writer.template_copy(d.ad_group_name, kw, rules.locations, json.loads(d.usps), brand)
    d.headlines, d.descriptions = json.dumps(copy.headlines), json.dumps(copy.descriptions)
    d.path1, d.path2, d.notes = copy.path1[:32], copy.path2[:32], copy.notes
    db.add(d)
    db.flush()
    _apply_checks(db, d)
    db.commit()
    log.info("ad_draft_created", extra={"draft_id": d.id, "mode": d.mode, "tokens_out": d.output_tokens})
    return d


def get_draft(db: DbSession, draft_id: int) -> AdDraft:
    d = db.get(AdDraft, draft_id)
    if d is None:
        raise NotFoundError("Draft not found", module_id=MODULE_ID)
    return d


def update_draft(db: DbSession, draft_id: int, fields: dict, by: str) -> AdDraft:
    d = get_draft(db, draft_id)
    before_status = d.status
    for k in ("headlines", "descriptions", "usps", "keywords"):
        if k in fields and fields[k] is not None:
            setattr(d, k, json.dumps([s.strip() for s in fields[k]]))
    for k in ("path1", "path2", "final_url", "ad_group_name", "campaign_name"):
        if fields.get(k) is not None:
            setattr(d, k, fields[k].strip())
    status = fields.get("status")
    if status is not None:
        if status not in ("draft", "approved", "rejected"):
            raise ValidationFailed("status must be draft, approved or rejected", module_id=MODULE_ID)
        d.status, d.reviewed_by = status, by
    _apply_checks(db, d)
    if d.status == "approved" and any(c.severity == "error" for c in checks_for(db, d.id)):
        db.rollback()
        raise ValidationFailed("Fix the errors (red) before approving — Google would reject this ad", module_id=MODULE_ID)
    if status is not None and status != before_status:
        audit_record(db, module_id=MODULE_ID, action=f"ad_draft_{status}", actor=by, entity_type="ad_draft", entity_id=d.id,
                    before={"status": before_status}, after={"status": status}, commit=False)
    db.commit()
    return d


def checks_for(db: DbSession, draft_id: int) -> list[ClaimCheck]:
    db.flush()
    return list(db.scalars(select(ClaimCheck).where(ClaimCheck.draft_id == draft_id).order_by(ClaimCheck.id)))


def list_drafts(db: DbSession, account_id: int, status: str | None) -> list[AdDraft]:
    q = select(AdDraft).where(AdDraft.account_id == account_id)
    if status:
        q = q.where(AdDraft.status == status)
    return list(db.scalars(q.order_by(AdDraft.id.desc())))


def draft_dict(db: DbSession, d: AdDraft) -> dict:
    return {"id": d.id, "account_id": d.account_id, "campaign_name": d.campaign_name, "ad_group_name": d.ad_group_name,
            "ad_group_google_id": d.ad_group_google_id, "final_url": d.final_url, "keywords": json.loads(d.keywords),
            "usps": json.loads(d.usps), "headlines": json.loads(d.headlines), "descriptions": json.loads(d.descriptions),
            "path1": d.path1, "path2": d.path2, "notes": d.notes, "mode": d.mode, "model": d.model,
            "output_tokens": d.output_tokens, "strength": d.strength, "status": d.status, "created_by": d.created_by,
            "reviewed_by": d.reviewed_by, "created_at": d.created_at, "updated_at": d.updated_at,
            "checks": [{"field": c.field, "index": c.index, "text": c.text, "code": c.code, "severity": c.severity,
                        "message": c.message} for c in checks_for(db, d.id)]}


def export_csv(db: DbSession, account_id: int) -> str:
    """Approved drafts in Google Ads Editor's responsive-search-ad column layout (import creates them PAUSED)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Campaign", "Ad group", *[f"Headline {i}" for i in range(1, 16)], *[f"Description {i}" for i in range(1, 5)],
                "Path 1", "Path 2", "Final URL", "Ad type", "Status"])
    for d in list_drafts(db, account_id, "approved"):
        hs, ds = json.loads(d.headlines)[:15], json.loads(d.descriptions)[:4]
        w.writerow([d.campaign_name, d.ad_group_name, *(hs + [""] * (15 - len(hs))), *(ds + [""] * (4 - len(ds))),
                    d.path1, d.path2, d.final_url, "Responsive search ad", "Paused"])
    return buf.getvalue()
