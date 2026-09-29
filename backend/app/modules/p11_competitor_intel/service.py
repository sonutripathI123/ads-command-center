"""P11 — competitor list, public-website research, manual Google observations, coverage/gap comparison and a separate,
labelled interpretation. Never claims competitors' private Google Ads data."""
import json
import re
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel.interface import list_websites, website_pages
from app.modules.p05_ads_sync.interface import list_accounts, search_terms
from app.modules.p11_competitor_intel import analysis, interpret, research
from app.modules.p11_competitor_intel.models import Competitor, CompetitorAnalysis, CompetitorObservation
from app.modules.p21_business_rules.interface import get_rules
from app.shared.errors import AppError, NotFoundError, ValidationFailed
from app.shared.feature_flags import is_enabled, require_enabled
from app.shared.logging import get_logger

MODULE_ID = "P11"
RESEARCH_FLAG = "competitor.research.enabled"
AI_FLAG = "ai.live_calls.enabled"  # declared by P14; read-only here
PLACEMENTS = ("ad", "organic", "maps")
log = get_logger(MODULE_ID)


class AIFailed(AppError):
    status_code = 502
    code = "ai_failed"


def _utc(v):
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    return v.replace(tzinfo=UTC) if v is not None and v.tzinfo is None else v


def account(db: DbSession, account_id: int):
    acc = next((a for a in list_accounts(db) if a.id == account_id), None)
    if acc is None:
        raise NotFoundError("Ads account not found or not active", module_id=MODULE_ID)
    return acc


def _site(url: str) -> tuple[str, str]:
    u = url.strip()
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    p = urlparse(u)
    host = p.netloc.lower()
    if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}(:\d+)?", host):
        raise ValidationFailed("Enter a valid website, e.g. example.com.au", module_id=MODULE_ID)
    return host.removeprefix("www."), f"{p.scheme.lower()}://{host}/"


def _own_domains(db: DbSession) -> set[str]:
    return {w.domain.lower().removeprefix("www.") for w in list_websites(db)}


# ---- competitors -----------------------------------------------------------------------------------

def add_competitor(db: DbSession, account_id: int, *, name: str, website: str, brand_terms: list[str], notes: str, by: str) -> Competitor:
    account(db, account_id)
    domain, base = _site(website)
    if domain in _own_domains(db):
        raise ValidationFailed("That is one of your own websites", module_id=MODULE_ID)
    existing = db.scalar(select(Competitor).where(Competitor.account_id == account_id, Competitor.domain == domain))
    if existing and existing.status == "active":
        raise ValidationFailed("This competitor is already in the list", module_id=MODULE_ID)
    if existing:  # archived → restore it (its earlier observations come back too)
        existing.status, existing.name = "active", name.strip() or existing.name
        if brand_terms:
            existing.brand_terms = json.dumps(sorted({t.strip().lower() for t in brand_terms if t.strip()}))
        if notes.strip():
            existing.notes = notes.strip()
        db.commit()
        return existing
    c = Competitor(account_id=account_id, name=name.strip(), domain=domain, base_url=base, notes=notes.strip(),
                   brand_terms=json.dumps(sorted({t.strip().lower() for t in brand_terms if t.strip()})), created_by=by)
    db.add(c)
    db.commit()
    return c


def get(db: DbSession, competitor_id: int) -> Competitor:
    c = db.get(Competitor, competitor_id)
    if c is None:
        raise NotFoundError("Competitor not found", module_id=MODULE_ID)
    return c


def update_competitor(db: DbSession, competitor_id: int, changes: dict) -> Competitor:
    c = get(db, competitor_id)
    if "name" in changes and changes["name"] is not None:
        c.name = changes["name"].strip() or c.name
    if changes.get("brand_terms") is not None:
        c.brand_terms = json.dumps(sorted({t.strip().lower() for t in changes["brand_terms"] if t.strip()}))
    if changes.get("notes") is not None:
        c.notes = changes["notes"].strip()
    if changes.get("status") is not None:
        if changes["status"] not in ("active", "archived"):
            raise ValidationFailed("status must be active or archived", module_id=MODULE_ID)
        c.status = changes["status"]
    db.commit()
    return c


def competitors(db: DbSession, account_id: int, *, include_archived: bool = False) -> list[Competitor]:
    q = select(Competitor).where(Competitor.account_id == account_id)
    if not include_archived:
        q = q.where(Competitor.status == "active")
    return list(db.scalars(q.order_by(Competitor.name)))


# ---- observations ----------------------------------------------------------------------------------

def run_research(db: DbSession, competitor_id: int, *, by: str, researcher=None) -> dict:
    c = get(db, competitor_id)
    require_enabled(RESEARCH_FLAG, db, module_id=MODULE_ID)
    r = get_rules(db, c.account_id)
    keywords = analysis.dedupe_terms(r.services + r.locations)
    pages, notes = (researcher or research.research)(c.base_url, keywords)
    ok = [p for p in pages if p.status_code and p.status_code < 400 and not p.error]
    if ok:  # keep older page observations as history, but only the latest run counts
        for o in db.scalars(select(CompetitorObservation).where(CompetitorObservation.competitor_id == c.id,
                                                                CompetitorObservation.kind == "page", CompetitorObservation.current)):
            o.current = False
    today = date.today()
    for p in ok:
        db.add(CompetitorObservation(competitor_id=c.id, kind="page", source=p.url, observed_on=today, data=json.dumps(p.to_dict()),
                                     created_by=by))
    failed = [f"{p.url}: {p.error or p.status_code}" for p in pages if p not in ok]
    c.last_researched_at = datetime.now(UTC)
    c.research_notes = json.dumps(notes + ([f"{len(failed)} page(s) could not be read"] if failed else []))
    db.commit()
    log.info("competitor_researched", extra={"competitor_id": c.id, "pages": len(ok)})
    return {"pages_read": len(ok), "failed": failed, "notes": notes}


def add_observation(db: DbSession, competitor_id: int, *, kind: str, data: dict, observed_on: date, by: str) -> CompetitorObservation:
    c = get(db, competitor_id)
    if kind == "serp":
        if not (data.get("query") or "").strip():
            raise ValidationFailed("Enter the search you made", module_id=MODULE_ID)
        if data.get("placement") not in PLACEMENTS:
            raise ValidationFailed(f"placement must be one of {PLACEMENTS}", module_id=MODULE_ID)
        pos = data.get("position")
        if pos is not None and not (isinstance(pos, int) and 1 <= pos <= 50):
            raise ValidationFailed("position must be 1–50", module_id=MODULE_ID)
        source = f"manual: {data['query'].strip()[:200]}"
    elif kind == "note":
        if not (data.get("text") or "").strip():
            raise ValidationFailed("Write the note", module_id=MODULE_ID)
        source = "manual note"
    else:
        raise ValidationFailed("kind must be serp or note", module_id=MODULE_ID)
    if observed_on > date.today():
        raise ValidationFailed("Date can't be in the future", module_id=MODULE_ID)
    clean = {k: (v.strip()[:2000] if isinstance(v, str) else v) for k, v in data.items() if k in ("query", "placement", "position", "text", "device", "location")}
    o = CompetitorObservation(competitor_id=c.id, kind=kind, source=source, observed_on=observed_on, data=json.dumps(clean), created_by=by)
    db.add(o)
    db.commit()
    return o


def delete_observation(db: DbSession, observation_id: int) -> None:
    o = db.get(CompetitorObservation, observation_id)
    if o is None:
        raise NotFoundError("Observation not found", module_id=MODULE_ID)
    if o.kind == "page":
        raise ValidationFailed("Website observations are replaced by re-running research", module_id=MODULE_ID)
    db.delete(o)
    db.commit()


def observations(db: DbSession, competitor_ids: list[int], *, current_only: bool = True) -> list[dict]:
    if not competitor_ids:
        return []
    q = select(CompetitorObservation).where(CompetitorObservation.competitor_id.in_(competitor_ids))
    if current_only:
        q = q.where(CompetitorObservation.current)
    return [{"id": o.id, "competitor_id": o.competitor_id, "kind": o.kind, "source": o.source, "observed_on": o.observed_on,
             "data": json.loads(o.data), "created_by": o.created_by, "created_at": _utc(o.created_at)}
            for o in db.scalars(q.order_by(CompetitorObservation.observed_on.desc(), CompetitorObservation.id.desc()))]


# ---- comparison ------------------------------------------------------------------------------------

def _our_profiles(db: DbSession, account_id: int, terms: list[str]) -> tuple[list[dict], int]:
    out = []
    sites = [w for w in list_websites(db) if w.ads_account_id == account_id]
    for w in sites:
        for p in website_pages(db, w.id):
            if p.get("status_code") and p["status_code"] >= 400:
                continue
            found = {t.lower() for t in p.get("services", []) + p.get("locations", [])}
            head = analysis.headline_text({"url": p["url"], "title": p.get("title", ""), "h1": [p.get("h1") or ""]})
            out.append({"mentions": {t for t in terms if t in found or analysis._has(head, t)},
                        "dedicated": {t for t in terms if analysis._has(head, t)}, "themes": []})
    return out, len(sites)


def overview(db: DbSession, account_id: int) -> dict:
    account(db, account_id)
    r = get_rules(db, account_id)
    services, locations = analysis.dedupe_terms(r.services), analysis.dedupe_terms(r.locations)
    comps = competitors(db, account_id)
    obs = observations(db, [c.id for c in comps])
    d2 = date.today()
    terms = search_terms(db, account_id, d2 - timedelta(days=364), d2, limit=10_000)
    ours, sites = _our_profiles(db, account_id, services + locations)
    theirs, out = {}, []
    for c in comps:
        pages = [o["data"] | {"url": o["source"]} for o in obs if o["competitor_id"] == c.id and o["kind"] == "page"]
        profs = [analysis.page_profile(p, services, locations) for p in pages]
        theirs[c.id] = profs
        out.append({"id": c.id, "name": c.name, "domain": c.domain, "base_url": c.base_url, "notes": c.notes,
                    "brand_terms": json.loads(c.brand_terms), "last_researched_at": _utc(c.last_researched_at),
                    "research_notes": json.loads(c.research_notes), "pages_read": len(pages),
                    "messaging": analysis.messaging(pages), "themes": analysis.themes(pages, profs),
                    "search_demand": analysis.search_demand(terms, analysis.brand_terms(c.name, c.domain, json.loads(c.brand_terms))),
                    "observations": [o for o in obs if o["competitor_id"] == c.id and o["kind"] != "page"]})
    names = {c.id: c.name for c in comps}
    researched = {cid: ps for cid, ps in theirs.items() if ps}
    svc, loc = analysis.coverage(ours, researched, services), analysis.coverage(ours, researched, locations)
    return {"competitors": out, "our_pages": len(ours), "our_sites": sites,
            "coverage": {"services": svc, "locations": loc},
            "gaps": {"services": analysis.gaps(svc, names), "locations": analysis.gaps(loc, names)},
            "research_enabled": is_enabled(RESEARCH_FLAG, db), "ai_live": ai_live(db)}


def ai_live(db: DbSession) -> bool:
    return is_enabled(AI_FLAG, db) and bool(interpret.P11Settings().anthropic_api_key)


def analyze(db: DbSession, account_id: int, *, use_ai: bool, by: str) -> CompetitorAnalysis:
    ov = overview(db, account_id)
    if not ov["competitors"]:
        raise ValidationFailed("Add at least one competitor first", module_id=MODULE_ID)
    comps = competitors(db, account_id)
    obs = observations(db, [c.id for c in comps])
    names = {c.id: c.name for c in comps}
    gap_rows = ov["gaps"]["services"]["gaps"] + ov["gaps"]["locations"]["gaps"]
    demand = {c["name"]: c["search_demand"] for c in ov["competitors"]}
    mode, model, tokens = "template", None, None
    if use_ai and ai_live(db):
        text, keys = interpret.evidence_block(obs, gap_rows, demand, names)
        try:
            res, tokens, model = interpret.with_claude(text, keys, interpret.P11Settings())
            mode = "live"
        except interpret.InterpretError as e:
            raise AIFailed(str(e), module_id=MODULE_ID) from e
    else:
        res = interpret.template(gap_rows, demand, {c["name"]: c["messaging"] for c in ov["competitors"]})
    row = CompetitorAnalysis(account_id=account_id, mode=mode, model=model, content=res.model_dump_json(),
                             observation_ids=json.dumps([o["id"] for o in obs]), output_tokens=tokens, created_by=by)
    db.add(row)
    db.commit()
    return row


def latest_analysis(db: DbSession, account_id: int) -> CompetitorAnalysis | None:
    return db.scalar(select(CompetitorAnalysis).where(CompetitorAnalysis.account_id == account_id)
                     .order_by(CompetitorAnalysis.id.desc()).limit(1))


def analysis_dict(a: CompetitorAnalysis | None) -> dict | None:
    if a is None:
        return None
    return {"id": a.id, "mode": a.mode, "model": a.model, "created_by": a.created_by, "created_at": _utc(a.created_at),
            "observations_used": len(json.loads(a.observation_ids)), "interpretation": json.loads(a.content)}


def summary(db: DbSession, account_id: int) -> dict:
    """For other modules (P14/P19): competitor names, gap terms and the latest interpretation's opportunities."""
    ov = overview(db, account_id)
    a = analysis_dict(latest_analysis(db, account_id))
    return {"competitors": [c["name"] for c in ov["competitors"]],
            "service_gaps": [g["term"] for g in ov["gaps"]["services"]["gaps"]],
            "location_gaps": [g["term"] for g in ov["gaps"]["locations"]["gaps"]],
            "opportunities": a["interpretation"]["opportunities"] if a else []}
