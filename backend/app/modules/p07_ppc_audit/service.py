"""P07 — gather data through other modules' interfaces, run checks, persist runs/issues."""
import json
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel.interface import landing_pages, list_websites, website_pages
from app.modules.p05_ads_sync import interface as ads
from app.modules.p06_analytics.interface import website_overview
from app.modules.p07_ppc_audit.checks import AuditData, run_checks, score
from app.modules.p07_ppc_audit.models import AuditIssue, AuditRun
from app.modules.p08_keyword_intel.interface import classify_terms
from app.modules.p21_business_rules.interface import get_rules
from app.shared.errors import NotFoundError, ValidationFailed
from app.shared.logging import get_logger

MODULE_ID = "P07"
log = get_logger(MODULE_ID)


def account(db: DbSession, account_id: int):
    acc = next((a for a in ads.list_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or not active", module_id=MODULE_ID)
    return acc


def gather(db: DbSession, account_id: int, days: int) -> tuple[AuditData, object | None, list[str]]:
    acc = account(db, account_id)
    d2 = date.today()
    d1 = d2 - timedelta(days=days - 1)
    errors: list[str] = []
    terms = ads.search_terms(db, account_id, d1, d2, limit=200_000)
    values = {t: v[1] for t, v in classify_terms(db, account_id, sorted({s["search_term"].lower() for s in terms})).items()}
    site = next((w for w in list_websites(db) if w.ads_account_id == account_id), None)
    tracking, lps, pages, organic = [], [], [], []
    if site is not None:
        try:
            ov = website_overview(db, site.id, d1, d2 - timedelta(days=1))
            tracking, organic = ov["health"], ov["top_queries"]
        except Exception as e:  # noqa: BLE001 — one source failing must not stop the audit
            errors.append(f"analytics: {str(e)[:200]}")
        try:
            lps, pages = landing_pages(db, site.id), website_pages(db, site.id)
        except Exception as e:  # noqa: BLE001
            errors.append(f"website: {str(e)[:200]}")
    data = AuditData(
        currency=acc.currency_code or "AUD", days=days, totals=ads.summary(db, account_id, d1, d2)["totals"],
        campaigns=ads.campaigns(db, account_id, d1, d2), ad_groups=ads.ad_groups(db, account_id, d1, d2),
        keywords=ads.keywords(db, account_id, d1, d2), search_terms=terms, ads=ads.ads(db, account_id, d1, d2),
        term_values=values, rules=get_rules(db, account_id), website=site, tracking=tracking, landing_pages=lps,
        pages=pages, organic_queries=organic)
    return data, site, errors


def run_audit(db: DbSession, account_id: int, days: int, *, by: str | None) -> AuditRun:
    if not 7 <= days <= 365:
        raise ValidationFailed("days must be between 7 and 365", module_id=MODULE_ID)
    data, site, errors = gather(db, account_id, days)
    issues = run_checks(data)
    dismissed = {i.fingerprint: i for i in db.scalars(select(AuditIssue).where(AuditIssue.ads_account_id == account_id,
                                                                              AuditIssue.status == "dismissed"))}
    counts = {s: sum(1 for i in issues if i.severity == s) for s in ("critical", "warning", "info")}
    run = AuditRun(ads_account_id=account_id, website_id=site.id if site else None, days=days, score=score(issues),
                   counts=json.dumps(counts), errors=json.dumps(errors), triggered_by=by)
    db.add(run)
    db.flush()
    for i in issues:
        fp = f"{i.code}|{i.entity_type}|{i.entity_id}"[:600]
        prev = dismissed.get(fp)
        db.add(AuditIssue(
            run_id=run.id, ads_account_id=account_id, fingerprint=fp, code=i.code, category=i.category, severity=i.severity,
            title=i.title[:2000], observation=i.observation, evidence=json.dumps(i.evidence), reasoning=i.reasoning,
            action=i.action, impact=i.impact, confidence=i.confidence, risk=i.risk, entity_type=i.entity_type,
            entity_id=i.entity_id[:512], link=i.link, status="dismissed" if prev else "open",
            dismissed_by=prev.dismissed_by if prev else None, dismiss_note=prev.dismiss_note if prev else None))
    db.commit()
    log.info("audit_done", extra={"run_id": run.id, "account_id": account_id, "score": run.score, "issues": len(issues)})
    return run


def latest(db: DbSession, account_id: int) -> tuple[AuditRun | None, list[AuditIssue]]:
    run = db.scalars(select(AuditRun).where(AuditRun.ads_account_id == account_id).order_by(AuditRun.id.desc()).limit(1)).first()
    if run is None:
        return None, []
    return run, list(db.scalars(select(AuditIssue).where(AuditIssue.run_id == run.id).order_by(AuditIssue.id)))


def history(db: DbSession, account_id: int, limit: int = 20) -> list[AuditRun]:
    return list(db.scalars(select(AuditRun).where(AuditRun.ads_account_id == account_id).order_by(AuditRun.id.desc()).limit(limit)))


def set_status(db: DbSession, issue_id: int, status: str, *, by: str, note: str | None) -> AuditIssue:
    if status not in ("open", "dismissed"):
        raise ValidationFailed("status must be open or dismissed", module_id=MODULE_ID)
    i = db.get(AuditIssue, issue_id)
    if i is None:
        raise NotFoundError("Issue not found", module_id=MODULE_ID)
    # apply to every run's copy so the decision sticks
    for same in db.scalars(select(AuditIssue).where(AuditIssue.ads_account_id == i.ads_account_id, AuditIssue.fingerprint == i.fingerprint)):
        same.status = status
        same.dismissed_by, same.dismiss_note = (by, note) if status == "dismissed" else (None, None)
    db.commit()
    return i
