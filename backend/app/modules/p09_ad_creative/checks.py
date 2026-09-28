"""P09 — responsive search ad (RSA) checks and existing-ad analysis. Pure functions.

Limits follow Google Ads RSA rules: headlines ≤ 30 chars (3–15), descriptions ≤ 90 chars (2–4), paths ≤ 15 chars.
Claim checks flag wording that needs proof unless the business listed it as an approved claim/USP.
"""
import re
from dataclasses import dataclass

H_MAX, D_MAX, P_MAX = 30, 90, 15
H_MIN, H_BEST, D_MIN, D_BEST = 3, 15, 2, 4

CLAIMS = [
    (r"#\s?1|\bno\.?\s?1\b|\bnumber one\b", "ranking claim ('#1')"),
    (r"\bbest\b", "superlative ('best')"),
    (r"\bcheapest\b|\blowest price", "price superlative"),
    (r"\bguarantee", "guarantee"),
    (r"\b(top rated|highest rated|award[- ]winning)\b", "rating/award claim"),
    (r"\b\d{1,3}\s?% off\b|\bfree\b", "offer ('free' / % off)"),
    (r"\$\s?\d", "price"),
]
CTA = re.compile(r"\b(book|reserve|get (a|an|your) (quote|price)|quote|call|enquire|contact|request)\b", re.I)
PHONE = re.compile(r"(?:\+?61|0)[\s\-()]*[2-478](?:[\s\-()]*\d){8}|1[38]00(?:[\s\-]*\d){6}")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


@dataclass
class Finding:
    field: str      # headline | description | path | ad
    index: int      # position in its list (-1 for whole ad)
    text: str
    code: str
    severity: str   # error (Google would reject / breaks rules) | warning (review)
    message: str


def _has(phrase: str, text: str) -> bool:
    return re.search(r"(?<![\w])" + re.escape(phrase.lower()) + r"(?![\w])", text.lower()) is not None


def check_text(field: str, i: int, text: str, *, approved_claims: list[str], competitors: list[str]) -> list[Finding]:
    out, limit = [], {"headline": H_MAX, "description": D_MAX, "path": P_MAX}[field]
    t = text.strip()
    f = lambda code, sev, msg: out.append(Finding(field, i, t, code, sev, msg))  # noqa: E731
    if not t:
        f("empty", "error", "Empty text")
        return out
    if len(t) > limit:
        f("too_long", "error", f"{len(t)}/{limit} characters — Google will reject it")
    if field == "headline" and "!" in t:
        f("exclamation_in_headline", "error", "Google doesn't allow '!' in headlines")
    if re.search(r"([!?.,])\1", t):
        f("repeated_punctuation", "error", "Repeated punctuation isn't allowed")
    if PHONE.search(t):
        f("phone_in_text", "error", "Phone numbers belong in a call asset, not ad text")
    if EMOJI.search(t):
        f("emoji", "error", "Emojis/symbols aren't allowed")
    caps = [w for w in re.findall(r"[A-Za-z]{4,}", t) if w.isupper()]
    if caps:
        f("all_caps", "error", f"Word(s) in capitals: {', '.join(caps[:3])} — Google limits excessive capitalisation")
    if field == "path" and re.search(r"[^A-Za-z0-9\-]", t):
        f("path_chars", "error", "Paths may only use letters, numbers and hyphens")
    for c in competitors:
        if _has(c, t):
            f("competitor_name", "error", f"Mentions competitor '{c}' (trademark risk)")
    approved = " ".join(approved_claims).lower()
    for rx, label in CLAIMS:
        m = re.search(rx, t, re.I)
        if m and m.group(0).lower().strip() not in approved:
            f("unverified_claim", "warning", f"{label} — keep only if you can prove it (add it to your USPs/approved claims)")
    return out


def check_ad(headlines: list[str], descriptions: list[str], paths: list[str], *, keywords: list[str], locations: list[str],
             approved_claims: list[str], competitors: list[str]) -> list[Finding]:
    out: list[Finding] = []
    kw = dict(approved_claims=approved_claims, competitors=competitors)
    for i, h in enumerate(headlines):
        out += check_text("headline", i, h, **kw)
    for i, d in enumerate(descriptions):
        out += check_text("description", i, d, **kw)
    for i, p in enumerate(paths):
        if p.strip():
            out += check_text("path", i, p, **kw)
    ad = lambda code, sev, msg: out.append(Finding("ad", -1, "", code, sev, msg))  # noqa: E731
    hs = [h.strip() for h in headlines if h.strip()]
    ds = [d.strip() for d in descriptions if d.strip()]
    if len(hs) < H_MIN:
        ad("too_few_headlines", "error", f"{len(hs)} headlines — at least {H_MIN} required")
    elif len(hs) < 8:
        ad("few_headlines", "warning", f"{len(hs)} headlines — add up to {H_BEST} for better Ad Strength")
    if len(hs) > H_BEST:
        ad("too_many_headlines", "error", f"{len(hs)} headlines — maximum {H_BEST}")
    if len(ds) < D_MIN:
        ad("too_few_descriptions", "error", f"{len(ds)} descriptions — at least {D_MIN} required")
    elif len(ds) < D_BEST:
        ad("few_descriptions", "warning", f"{len(ds)} descriptions — use {D_BEST}")
    if len(ds) > D_BEST:
        ad("too_many_descriptions", "error", f"{len(ds)} descriptions — maximum {D_BEST}")
    lower = [h.lower() for h in hs]
    dups = {h for h in lower if lower.count(h) > 1}
    if dups:
        ad("duplicate_headlines", "error", f"Duplicate headlines: {', '.join(sorted(dups))[:120]}")
    text = " ".join(hs + ds)
    if keywords and not any(_has(k, " ".join(hs)) for k in keywords[:10]):
        ad("no_keyword_in_headlines", "warning", "No headline contains one of the ad group's main keywords")
    if not CTA.search(text):
        ad("no_call_to_action", "warning", "No call to action (Book / Get a quote / Call)")
    if locations and not any(_has(l, text) for l in locations):
        ad("no_location", "warning", "No area mentioned (e.g. Melbourne)")
    return out


def strength(headlines: list[str], descriptions: list[str], findings: list[Finding]) -> int:
    """0–100 proxy for Google's Ad Strength (Google's own rating is not available via our read access)."""
    hs, ds = len([h for h in headlines if h.strip()]), len([d for d in descriptions if d.strip()])
    s = min(hs, 15) / 15 * 50 + min(ds, 4) / 4 * 20 + 30
    s -= 10 * sum(1 for f in findings if f.severity == "error")
    s -= 4 * sum(1 for f in findings if f.severity == "warning" and f.field == "ad")
    return max(0, min(100, round(s)))
