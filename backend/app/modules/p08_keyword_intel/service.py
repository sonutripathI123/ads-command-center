"""P08 — run analysis over P05 data with P21 rules; persist classifications and candidates; review decisions."""
import csv
import io
import json
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p05_ads_sync.interface import campaigns, keywords, list_accounts, search_terms
from app.modules.p08_keyword_intel.analysis import Classifier, keyword_insights, negative_candidates
from app.modules.p08_keyword_intel.models import KeywordCandidate, NegativeKeywordCandidate, SearchTermClassification
from app.modules.p21_business_rules.interface import get_rules
from app.shared.errors import NotFoundError, ValidationFailed
from app.shared.logging import get_logger

MODULE_ID = "P08"
STATUSES = ("proposed", "accepted", "rejected")
log = get_logger(MODULE_ID)


def check_account(db: DbSession, account_id: int) -> None:
    if not any(a.id == account_id for a in list_accounts(db)):
        raise NotFoundError("Ads account not found or not active", module_id=MODULE_ID)


def analyze(db: DbSession, account_id: int, d1: date, d2: date) -> dict:
    check_account(db, account_id)
    clf = Classifier(get_rules(db, account_id))
    terms = search_terms(db, account_id, d1, d2, limit=200_000)
    kws = keywords(db, account_id, d1, d2)

    # classifications (one row per distinct term)
    existing = {c.term: c for c in db.scalars(select(SearchTermClassification).where(SearchTermClassification.account_id == account_id))}
    counts: dict[str, int] = {}
    for term in {" ".join(t["search_term"].lower().split()) for t in terms}:
        intent, value, reasons = clf.classify(term)
        counts[intent] = counts.get(intent, 0) + 1
        row = existing.get(term) or SearchTermClassification(account_id=account_id, term=term)
        row.intent, row.business_value, row.reasons = intent, value, json.dumps(reasons)
        db.add(row)

    # negative candidates: upsert, keep review status; mark proposals no longer found as stale
    found = negative_candidates(terms, clf)
    old = {(c.text, c.match_type, c.campaign_key): c for c in
           db.scalars(select(NegativeKeywordCandidate).where(NegativeKeywordCandidate.account_id == account_id))}
    seen = set()
    for c in found:
        key = (c.text, c.match_type, c.campaign_google_id or "")
        seen.add(key)
        row = old.get(key) or NegativeKeywordCandidate(account_id=account_id, text=c.text, match_type=c.match_type,
                                                       campaign_key=c.campaign_google_id or "", status="proposed")
        row.source, row.confidence, row.reason = c.source, c.confidence, c.reason
        row.cost, row.clicks, row.impressions, row.conversions = c.cost, c.clicks, c.impressions, c.conversions
        row.term_count, row.examples, row.window_from, row.window_to = c.term_count, json.dumps(c.examples), d1, d2
        if row.status == "stale":
            row.status = "proposed"
        db.add(row)
    for key, row in old.items():
        if key not in seen and row.status == "proposed":
            row.status = "stale"

    # expansion candidates
    ins = keyword_insights(kws, terms, clf)
    old_kc = {(k.text, k.ad_group_google_id): k for k in
              db.scalars(select(KeywordCandidate).where(KeywordCandidate.account_id == account_id))}
    for t in ins["expansion_candidates"]:
        text = " ".join(t["search_term"].lower().split())
        row = old_kc.get((text, t["ad_group_google_id"])) or KeywordCandidate(
            account_id=account_id, text=text, campaign_google_id=t["campaign_google_id"],
            ad_group_google_id=t["ad_group_google_id"])
        row.reason, row.cost, row.clicks, row.conversions = t["reason"], t["cost"], t["clicks"], t["conversions"]
        db.add(row)
    db.commit()
    total_neg = sum(c.cost for c in found if c.confidence >= 0.8)
    log.info("analysis_done", extra={"account_id": account_id, "terms": len(terms), "negatives": len(found)})
    return {"date_from": d1, "date_to": d2, "search_terms": len(terms), "intents": counts,
            "negative_candidates": len(found), "high_confidence_waste": round(total_neg, 2),
            "expansion_candidates": len(ins["expansion_candidates"])}


def _campaign_names(db: DbSession, account_id: int, d1: date, d2: date) -> dict[str, str]:
    return {c["google_id"]: c["name"] for c in campaigns(db, account_id, d1, d2)}


def list_negatives(db: DbSession, account_id: int, *, status: str | None, min_confidence: float) -> list[dict]:
    q = select(NegativeKeywordCandidate).where(NegativeKeywordCandidate.account_id == account_id,
                                               NegativeKeywordCandidate.confidence >= min_confidence)
    q = q.where(NegativeKeywordCandidate.status == status) if status else q.where(NegativeKeywordCandidate.status != "stale")
    rows = list(db.scalars(q))
    names = _campaign_names(db, account_id, min((r.window_from for r in rows), default=date.today()),
                            max((r.window_to for r in rows), default=date.today())) if rows else {}
    return sorted([{
        "id": r.id, "text": r.text, "match_type": r.match_type, "campaign_google_id": r.campaign_key or None,
        "campaign_name": names.get(r.campaign_key) if r.campaign_key else None, "level": "campaign" if r.campaign_key else "account",
        "source": r.source, "confidence": r.confidence, "reason": r.reason, "cost": r.cost, "clicks": r.clicks,
        "impressions": r.impressions, "conversions": r.conversions, "term_count": r.term_count,
        "examples": json.loads(r.examples), "status": r.status, "reviewed_by": r.reviewed_by,
        "window_from": r.window_from, "window_to": r.window_to} for r in rows],
        key=lambda r: (-r["confidence"], -r["cost"]))


def review(db: DbSession, account_id: int, ids: list[int], status: str, email: str) -> int:
    if status not in STATUSES:
        raise ValidationFailed(f"status must be one of {STATUSES}", module_id=MODULE_ID)
    rows = list(db.scalars(select(NegativeKeywordCandidate).where(NegativeKeywordCandidate.account_id == account_id,
                                                                 NegativeKeywordCandidate.id.in_(ids))))
    for r in rows:
        r.status, r.reviewed_by, r.reviewed_at = status, email, datetime.now(UTC)
    db.commit()
    return len(rows)


def negatives_export(db: DbSession, account_id: int, fmt: str) -> str:
    """Accepted candidates, for manual upload. fmt=text → Google Ads UI box; fmt=csv → Google Ads Editor."""
    rows = list_negatives(db, account_id, status="accepted", min_confidence=0)
    if fmt == "text":
        return "\n".join(f'"{r["text"]}"' if r["match_type"] == "PHRASE" else f"[{r['text']}]" for r in rows) + "\n"
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Campaign", "Keyword", "Criterion Type", "Level", "Cost", "Clicks", "Conversions", "Reason"])
    for r in rows:
        w.writerow([r["campaign_name"] or "", r["text"], f"Negative {r['match_type'].title()}",
                    r["level"], r["cost"], r["clicks"], r["conversions"], r["reason"]])
    return buf.getvalue()


def classifications(db: DbSession, account_id: int, d1: date, d2: date, intent: str | None) -> list[dict]:
    cls = {c.term: c for c in db.scalars(select(SearchTermClassification).where(SearchTermClassification.account_id == account_id))}
    out = []
    for t in search_terms(db, account_id, d1, d2, limit=200_000):
        c = cls.get(" ".join(t["search_term"].lower().split()))
        if c is None or (intent and c.intent != intent):
            continue
        out.append({**t, "intent": c.intent, "business_value": c.business_value, "reasons": json.loads(c.reasons)})
    return out


def insights(db: DbSession, account_id: int, d1: date, d2: date) -> dict:
    check_account(db, account_id)
    clf = Classifier(get_rules(db, account_id))
    enabled = {c["google_id"] for c in campaigns(db, account_id, d1, d2) if c["status"] == "ENABLED"}
    ins = keyword_insights(keywords(db, account_id, d1, d2), search_terms(db, account_id, d1, d2, limit=200_000), clf,
                           enabled_campaigns=enabled)
    ins["enabled_campaigns"] = len(enabled)
    return ins
