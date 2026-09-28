"""P08 — pure, deterministic analysis (no DB, no network). Rules come from P21, performance from P05.

Every output carries its evidence (spend, clicks, conversions, example search terms) and a plain-English
reason, so a human can check it before acting. Nothing here changes Google Ads.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field

from app.modules.p21_business_rules.interface import Rules

STOPWORDS = {
    "a", "an", "and", "the", "to", "from", "for", "of", "in", "on", "at", "near", "me", "my", "with", "by", "is",
    "are", "best", "top", "good", "service", "services", "hire", "book", "booking", "price", "prices", "cost",
    "rates", "rate", "quote", "company", "companies", "australia", "au", "online", "vs", "or", "how", "much",
}


def _pattern(phrases: list[str]) -> list[tuple[str, re.Pattern]]:
    return [(p, re.compile(r"(?<![\w])" + re.escape(p) + r"(?![\w])")) for p in phrases if p]


def _hits(term: str, pats: list[tuple[str, re.Pattern]]) -> list[str]:
    return [p for p, rx in pats if rx.search(term)]


@dataclass
class Classifier:
    rules: Rules
    _p: dict = field(default_factory=dict)

    def __post_init__(self):
        r = self.rules
        self._p = {k: _pattern(getattr(r, k)) for k in
                   ("services", "locations", "other_locations", "excluded_terms", "competitor_terms", "brand_terms")}

    def hits(self, term: str) -> dict[str, list[str]]:
        t = " ".join(term.lower().split())
        return {k: _hits(t, v) for k, v in self._p.items()}

    def classify(self, term: str) -> tuple[str, str, list[str]]:
        """→ (intent, business_value, reasons). value: high | medium | low | negative | unknown."""
        h = self.hits(term)
        if h["excluded_terms"]:
            return "excluded", "negative", [f"contains excluded term '{x}'" for x in h["excluded_terms"]]
        if h["other_locations"] and not h["locations"]:
            return "wrong_location", "negative", [f"mentions '{x}', which you don't serve" for x in h["other_locations"]]
        if h["competitor_terms"]:
            return "competitor", "low", [f"competitor name '{x}'" for x in h["competitor_terms"]]
        if h["brand_terms"]:
            return "brand", "high", [f"your brand '{x}'" for x in h["brand_terms"]]
        if h["services"] and h["locations"]:
            return "service_location", "high", [f"service '{h['services'][0]}' + area '{h['locations'][0]}'"]
        if h["services"]:
            return "service", "medium", [f"service '{h['services'][0]}', no area"]
        if h["locations"]:
            return "location_only", "low", [f"area '{h['locations'][0]}' but no service word"]
        return "unclassified", "unknown", ["no service, area or excluded word recognised"]


@dataclass
class NegativeCandidate:
    text: str
    match_type: str  # PHRASE | EXACT
    campaign_google_id: str | None  # None = account level / shared negative list
    source: str  # excluded_term | wrong_location | no_conversions | pattern
    confidence: float
    reason: str
    cost: float = 0.0
    clicks: int = 0
    impressions: int = 0
    conversions: float = 0.0
    term_count: int = 0
    examples: list[str] = field(default_factory=list)
    mixed: list[str] = field(default_factory=list)  # matching searches that also contain one of your service words


def _agg(c: NegativeCandidate, t: dict) -> None:
    c.cost = round(c.cost + t["cost"], 2)
    c.clicks += t["clicks"]
    c.impressions += t["impressions"]
    c.conversions = round(c.conversions + t["conversions"], 2)
    c.term_count += 1
    if len(c.examples) < 5:
        c.examples.append(t["search_term"])


ALREADY_NEGATIVE = {"EXCLUDED", "ADDED_EXCLUDED"}


def negative_candidates(terms: list[dict], clf: Classifier) -> list[NegativeCandidate]:
    """terms: P05 search_terms rows (search_term, status, campaign_google_id, cost, clicks, impressions, conversions)."""
    r = clf.rules
    phrase: dict[str, NegativeCandidate] = {}
    exact: dict[tuple[str, str], NegativeCandidate] = {}
    words: dict[str, NegativeCandidate] = {}
    protected = set(r.services) | set(r.locations) | set(r.brand_terms)

    for t in terms:
        if t.get("status") in ALREADY_NEGATIVE or not t["search_term"]:
            continue
        term = " ".join(t["search_term"].lower().split())
        h = clf.hits(term)
        # 1) phrase negatives on the rule word itself (covers every future search containing it)
        for word in h["excluded_terms"]:
            c = phrase.setdefault(word, NegativeCandidate(word, "PHRASE", None, "excluded_term", 0.95,
                                                          f"'{word}' is on your excluded list"))
            _agg(c, t)
            if h["services"] and len(c.mixed) < 3:
                c.mixed.append(term)
        if not h["locations"]:
            for loc in h["other_locations"]:
                c = phrase.setdefault(loc, NegativeCandidate(loc, "PHRASE", None, "wrong_location", 0.85,
                                                             f"'{loc}' is a place you don't serve"))
                _agg(c, t)
        if h["excluded_terms"] or (h["other_locations"] and not h["locations"]):
            continue
        # 2) exact negatives for costly, non-converting, not clearly relevant terms
        intent, value, _ = clf.classify(term)
        if (t["conversions"] == 0 and t["cost"] >= r.min_spend_for_negative and t["clicks"] >= r.min_clicks_for_negative
                and value in ("low", "unknown")):
            key = (term, t["campaign_google_id"])
            c = exact.setdefault(key, NegativeCandidate(
                term, "EXACT", t["campaign_google_id"], "no_conversions", 0.6 if value == "unknown" else 0.5,
                f"{intent.replace('_', ' ')}: spent without any conversion"))
            _agg(c, t)
        # 3) data-driven words: frequent in non-converting terms, not a service/area/brand word
        if value != "high":
            for w in set(re.findall(r"[a-z0-9']+", term)):
                if w in STOPWORDS or w.isdigit() or len(w) < 3 or any(w in p.split() for p in protected):
                    continue
                c = words.setdefault(w, NegativeCandidate(w, "PHRASE", None, "pattern", 0.4,
                                                          f"'{w}' appears in several non-converting searches"))
                _agg(c, t)

    out = [c for c in phrase.values() if c.cost > 0 or c.clicks > 0]
    for c in out:
        if c.mixed and len(c.text.split()) > 1:  # e.g. 'rent a car with a chauffeur' ('chauffeur jobs' stays high)
            c.confidence = min(c.confidence, 0.6)
            c.reason += (f" — but some of these searches also mention your services (e.g. '{c.mixed[0]}'); "
                         "a phrase negative would block those too")
        if c.conversions > 0:  # the rule word still brought conversions → be careful
            c.confidence = min(c.confidence, 0.5)
            c.reason += f" — it brought {c.conversions:g} conversion(s), check before adding"
    covered = {c.text for c in out}
    out += [c for c in exact.values()
            if not any(re.search(r"(?<![\w])" + re.escape(w) + r"(?![\w])", c.text) for w in covered)]
    for c in words.values():
        if (c.term_count >= 3 and c.conversions == 0 and c.cost >= 2 * r.min_spend_for_negative
                and c.text not in covered):
            out.append(c)
    return sorted(out, key=lambda c: (-c.confidence, -c.cost))


def keyword_insights(keywords: list[dict], terms: list[dict], clf: Classifier,
                     enabled_campaigns: set[str] | None = None) -> dict[str, list[dict]]:
    """keywords/terms: P05 rows. Returns buckets of rows, each with a `reason`.

    `idle` and `duplicates` only look at enabled keywords in enabled campaigns (paused/cloned campaigns would
    otherwise flood them); duplicates are counted within one campaign.
    """
    r = clf.rules
    enabled = [k for k in keywords if k.get("status") == "ENABLED"
               and (enabled_campaigns is None or k.get("campaign_google_id") in enabled_campaigns)]
    wasters = [dict(k, reason=f"spent without a conversion ({k['clicks']} clicks)") for k in keywords
               if k["conversions"] == 0 and k["cost"] >= r.min_spend_for_negative and k["clicks"] >= r.min_clicks_for_negative]
    winners = sorted([dict(k, reason="brings conversions") for k in keywords if k["conversions"] > 0],
                     key=lambda k: k["cost_per_conversion"] or 0)
    target = r.target_cost_per_conversion
    if target:
        for w in winners:
            if w["cost_per_conversion"] and w["cost_per_conversion"] > target:
                w["reason"] = f"converts, but above your target of ${target:g} per conversion"
    low_qs = [dict(k, reason=f"Quality Score {k['quality_score']}/10 — raises your CPC") for k in keywords
              if k.get("quality_score") is not None and k["quality_score"] <= 4 and k["impressions"] > 0]
    idle = [dict(k, reason="enabled but no impressions in this period") for k in enabled if k["impressions"] == 0]
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for k in enabled:
        groups[(k.get("campaign_google_id") or "", k["text"].lower(), k.get("match_type") or "")].append(k)
    duplicates = [dict(ks[0], reason=f"same keyword in {len(ks)} ad groups: " + ", ".join(sorted({x['ad_group_name'] for x in ks})))
                  for ks in groups.values() if len(ks) > 1]
    existing = {k["text"].lower() for k in keywords}
    expansions = []
    for t in terms:
        term = " ".join(t["search_term"].lower().split())
        if t["conversions"] > 0 and t.get("status") in (None, "NONE") and term not in existing:
            intent, value, _ = clf.classify(term)
            if value != "negative":
                expansions.append(dict(t, reason=f"converted {t['conversions']:g}× but isn't a keyword yet ({intent.replace('_', ' ')})"))
    expansions.sort(key=lambda t: -t["conversions"])
    return {"wasters": sorted(wasters, key=lambda k: -k["cost"]), "winners": winners, "low_quality_score": low_qs,
            "idle": idle, "duplicates": duplicates, "expansion_candidates": expansions}
