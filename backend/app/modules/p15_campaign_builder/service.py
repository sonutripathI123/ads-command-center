"""P15 — build, edit, write ads for, approve and export draft campaigns. Draft / paused only."""
import csv
import io
import json
from dataclasses import asdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel.interface import landing_pages, list_websites, website_pages
from app.modules.p05_ads_sync.interface import keywords as ads_keywords
from app.modules.p05_ads_sync.interface import list_accounts
from app.modules.p06_analytics.interface import tracking_health
from app.modules.p08_keyword_intel.interface import accepted_negatives, classify_terms
from app.modules.p09_ad_creative.interface import get_draft as get_ad_draft
from app.modules.p09_ad_creative.interface import write_rsa
from app.modules.p15_campaign_builder import builder
from app.modules.p15_campaign_builder.models import CampaignDraft
from app.modules.p21_business_rules.interface import get_rules
from app.shared.errors import NotFoundError, ValidationFailed
from app.shared.logging import get_logger

MODULE_ID = "P15"
MAX_PER_GROUP = 30
log = get_logger(MODULE_ID)


def account(db: DbSession, account_id: int):
    acc = next((a for a in list_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or not active", module_id=MODULE_ID)
    return acc


def _website(db: DbSession, account_id: int, website_id: int | None):
    sites = list_websites(db)
    if website_id is not None:
        w = next((s for s in sites if s.id == website_id), None)
        if w is None:
            raise ValidationFailed("Unknown website", module_id=MODULE_ID)
        return w
    return next((s for s in sites if s.ads_account_id == account_id), None)


def _tracking(db: DbSession, site) -> list[str]:
    if site is None:
        return ["No website linked to this account"]
    d2 = date.today() - timedelta(days=1)
    try:
        return [h["title"] for h in tracking_health(db, site.id, d2 - timedelta(days=29), d2) if h["severity"] == "critical"]
    except Exception as e:  # noqa: BLE001 — a failing source must not block drafting
        return [f"Tracking check unavailable: {str(e)[:120]}"]


def build(db: DbSession, account_id: int, *, name: str, goal: str, source_ad_groups: list[str], website_id: int | None,
          themes: list[str] | None, daily_budget: float, max_cpc: float, by: str) -> CampaignDraft:
    account(db, account_id)
    if themes:
        bad = [t for t in themes if t not in builder.THEME_BY_KEY]
        if bad:
            raise ValidationFailed(f"Unknown theme(s): {bad}", module_id=MODULE_ID, details={"themes": list(builder.THEME_BY_KEY)})
    d2 = date.today()
    d1 = d2 - timedelta(days=89)
    kws = [k for k in ads_keywords(db, account_id, d1, d2) if k.get("status") != "REMOVED"
           and (not source_ad_groups or k["ad_group_google_id"] in source_ad_groups)]
    if not kws:
        raise ValidationFailed("No keywords found in the chosen ad groups — sync the account first", module_id=MODULE_ID)
    texts = sorted({" ".join(k["text"].lower().split()) for k in kws})
    values = {t: v[1] for t, v in classify_terms(db, account_id, texts).items()}
    groups, unassigned, negs = builder.cluster(kws, values, themes)
    rules = get_rules(db, account_id)
    site = _website(db, account_id, website_id)
    pages = website_pages(db, site.id) if site else []
    area = (site.location if site and site.location else (rules.locations[0].title() if rules.locations else "")).strip()
    ad_groups = []
    for key, label, _ in builder.THEMES:
        if key not in groups:
            continue
        ks = groups[key]
        url, score, why = builder.best_landing_page(key, pages, site.base_url if site else "")
        ad_groups.append({"key": key, "theme": label, "name": f"{label} {area}".strip()[:255],
                          "keywords": [asdict(k) for k in ks[:MAX_PER_GROUP]],
                          "reserve": [asdict(k) for k in ks[MAX_PER_GROUP:]],
                          "final_url": url if site else "", "landing_score": score, "landing_reason": why,
                          "ad_draft_id": None})
    seen, negatives = set(), []
    for n in negs + builder.default_negatives(rules.excluded_terms, rules.other_locations) + \
            [{"text": a["text"], "match_type": a["match_type"], "reason": "accepted in Negative keyword suggestions"}
             for a in accepted_negatives(db, account_id)]:
        if n["text"] not in seen:
            seen.add(n["text"])
            negatives.append(n)
    tracking = _tracking(db, site)
    settings = builder.default_settings(daily_budget=daily_budget, max_cpc=max_cpc, tracking_ok=not tracking,
                                        locations=rules.locations)
    d = CampaignDraft(account_id=account_id, website_id=site.id if site else None, name=name.strip()[:255], goal=goal[:2000],
                      source=json.dumps({"ad_groups": source_ad_groups, "keywords_in": len(kws), "window_days": 90}),
                      settings=json.dumps(settings), ad_groups=json.dumps(ad_groups),
                      unassigned=json.dumps([asdict(k) for k in unassigned]), negatives=json.dumps(negatives),
                      tracking_issues=json.dumps(tracking), created_by=by)
    db.add(d)
    db.commit()
    log.info("campaign_draft_built", extra={"draft_id": d.id, "ad_groups": len(ad_groups), "negatives": len(negatives)})
    return d


def get(db: DbSession, draft_id: int) -> CampaignDraft:
    d = db.get(CampaignDraft, draft_id)
    if d is None:
        raise NotFoundError("Campaign draft not found", module_id=MODULE_ID)
    return d


def _groups_with_ads(db: DbSession, d: CampaignDraft) -> list[dict]:
    out = []
    for g in json.loads(d.ad_groups):
        ad = get_ad_draft(db, g["ad_draft_id"]) if g.get("ad_draft_id") else None
        out.append({**g, "ad_status": ad["status"] if ad else None, "ad_strength": ad["strength"] if ad else None,
                    "ad_headlines": ad["headlines"][:3] if ad else []})
    return out


def draft_dict(db: DbSession, d: CampaignDraft) -> dict:
    groups = _groups_with_ads(db, d)
    settings = json.loads(d.settings)
    lps = []
    if d.website_id:
        lp_status = {lp["final_url"]: lp["status"] for lp in landing_pages(db, d.website_id)}
        lps = [lp_status.get(g["final_url"], "ok") for g in groups]
    negs = json.loads(d.negatives)
    return {"id": d.id, "account_id": d.account_id, "website_id": d.website_id, "name": d.name, "goal": d.goal,
            "status": d.status, "settings": settings, "ad_groups": groups, "unassigned": json.loads(d.unassigned),
            "negatives": negs, "tracking_issues": json.loads(d.tracking_issues), "source": json.loads(d.source),
            "checklist": builder.checklist(tracking_critical=json.loads(d.tracking_issues), landing=lps, ad_groups=groups,
                                           negatives=len(negs), settings=settings),
            "created_by": d.created_by, "approved_by": d.approved_by, "created_at": d.created_at, "updated_at": d.updated_at}


def list_drafts(db: DbSession, account_id: int) -> list[CampaignDraft]:
    return list(db.scalars(select(CampaignDraft).where(CampaignDraft.account_id == account_id,
                                                       CampaignDraft.status != "archived").order_by(CampaignDraft.id.desc())))


def _editable(d: CampaignDraft) -> None:
    if d.status != "draft":
        raise ValidationFailed("Move the campaign back to draft before editing", module_id=MODULE_ID)


def edit(db: DbSession, draft_id: int, op: dict, by: str) -> CampaignDraft:
    """Ops: rename_group · set_url · move_keyword · remove_keyword · add_negative · remove_negative · settings · rename."""
    d = get(db, draft_id)
    kind = op.get("op")
    if kind == "status":
        return set_status(db, d, op.get("status", ""), by)
    _editable(d)
    groups = json.loads(d.ad_groups)
    by_key = {g["key"]: g for g in groups}
    unassigned = json.loads(d.unassigned)
    negs = json.loads(d.negatives)

    def grp(key):
        if key not in by_key:
            raise ValidationFailed(f"Unknown ad group '{key}'", module_id=MODULE_ID)
        return by_key[key]

    if kind == "rename_group":
        grp(op["group"])["name"] = str(op["name"]).strip()[:255]
    elif kind == "set_url":
        grp(op["group"])["final_url"] = str(op["url"]).strip()[:1024]
    elif kind in ("move_keyword", "remove_keyword"):
        text, src = op["text"], op.get("from")
        pool = unassigned if src in (None, "unassigned") else grp(src)["keywords"]
        kw = next((k for k in pool if k["text"] == text), None)
        if kw is None:
            raise ValidationFailed(f"Keyword '{text}' not found", module_id=MODULE_ID)
        pool.remove(kw)
        if kind == "move_keyword":
            to = op["to"]
            (unassigned if to == "unassigned" else grp(to)["keywords"]).append(kw)
    elif kind == "add_negative":
        t = " ".join(str(op["text"]).lower().split())
        if t and all(n["text"] != t for n in negs):
            negs.append({"text": t, "match_type": op.get("match_type", "PHRASE"), "reason": f"added by {by}"})
    elif kind == "remove_negative":
        negs = [n for n in negs if n["text"] != op["text"]]
    elif kind == "settings":
        s = json.loads(d.settings)
        if "daily_budget" in op:
            s["daily_budget"] = max(0.0, float(op["daily_budget"]))
        if "max_cpc" in op and s["bidding"]["strategy"] == "MAXIMIZE_CLICKS":
            s["bidding"]["max_cpc"] = max(0.0, float(op["max_cpc"]))
        d.settings = json.dumps(s)
    elif kind == "rename":
        d.name = str(op["name"]).strip()[:255]
    else:
        raise ValidationFailed(f"Unknown edit op '{kind}'", module_id=MODULE_ID)
    d.ad_groups, d.unassigned, d.negatives = json.dumps(groups), json.dumps(unassigned), json.dumps(negs)
    db.commit()
    return d


def write_ads(db: DbSession, draft_id: int, group_key: str, *, usps: list[str], use_ai: bool, by: str) -> CampaignDraft:
    d = get(db, draft_id)
    _editable(d)
    groups = json.loads(d.ad_groups)
    g = next((x for x in groups if x["key"] == group_key), None)
    if g is None:
        raise ValidationFailed(f"Unknown ad group '{group_key}'", module_id=MODULE_ID)
    ad = write_rsa(db, d.account_id, ad_group_name=g["name"], campaign_name=d.name, final_url=g["final_url"],
                   keywords=[k["text"] for k in g["keywords"][:15]], usps=usps, use_ai=use_ai, by=by)
    g["ad_draft_id"] = ad["id"]
    d.ad_groups = json.dumps(groups)
    db.commit()
    return d


def set_status(db: DbSession, d: CampaignDraft, status: str, by: str) -> CampaignDraft:
    if status not in ("draft", "approved", "archived"):
        raise ValidationFailed("status must be draft, approved or archived", module_id=MODULE_ID)
    if status == "approved":
        blocking = [i for i in draft_dict(db, d)["checklist"] if i["status"] == "fail" and i["key"] != "tracking"]
        if blocking:
            raise ValidationFailed("Not ready: " + "; ".join(i["label"] for i in blocking), module_id=MODULE_ID,
                                   details={"blocking": [i["key"] for i in blocking]})
        d.approved_by = by
    d.status = status
    db.commit()
    return d


def export_csv(db: DbSession, draft_id: int) -> str:
    """Google Ads Editor import sheet: campaign, ad groups, keywords, campaign negatives and RSAs — everything paused."""
    d = get(db, draft_id)
    if d.status != "approved":
        raise ValidationFailed("Approve the campaign draft before exporting", module_id=MODULE_ID)
    s = json.loads(d.settings)
    cols = ["Campaign", "Campaign Type", "Campaign Status", "Budget", "Bid Strategy Type", "Max CPC", "Networks",
            "Ad group", "Ad group status", "Keyword", "Criterion Type", "Final URL",
            *[f"Headline {i}" for i in range(1, 16)], *[f"Description {i}" for i in range(1, 5)], "Path 1", "Path 2", "Ad type", "Status"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    bid = "Maximize clicks" if s["bidding"]["strategy"] == "MAXIMIZE_CLICKS" else "Maximize conversions"
    w.writerow({"Campaign": d.name, "Campaign Type": "Search", "Campaign Status": "Paused", "Budget": s["daily_budget"],
                "Bid Strategy Type": bid, "Max CPC": s["bidding"].get("max_cpc", ""), "Networks": "Google search"})
    for n in json.loads(d.negatives):
        w.writerow({"Campaign": d.name, "Keyword": n["text"], "Criterion Type": f"Negative {n['match_type'].title()}"})
    for g in json.loads(d.ad_groups):
        w.writerow({"Campaign": d.name, "Ad group": g["name"], "Ad group status": "Paused"})
        for k in g["keywords"]:
            w.writerow({"Campaign": d.name, "Ad group": g["name"], "Keyword": k["text"], "Criterion Type": k["match_type"].title(),
                        "Final URL": g["final_url"], "Status": "Paused"})
        ad = get_ad_draft(db, g["ad_draft_id"]) if g.get("ad_draft_id") else None
        if ad:
            row = {"Campaign": d.name, "Ad group": g["name"], "Final URL": ad["final_url"] or g["final_url"],
                   "Path 1": ad["path1"], "Path 2": ad["path2"], "Ad type": "Responsive search ad", "Status": "Paused"}
            row |= {f"Headline {i + 1}": h for i, h in enumerate(ad["headlines"][:15])}
            row |= {f"Description {i + 1}": x for i, x in enumerate(ad["descriptions"][:4])}
            w.writerow(row)
    return buf.getvalue()
