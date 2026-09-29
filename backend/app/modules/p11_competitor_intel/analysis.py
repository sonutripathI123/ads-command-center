"""P11 — pure comparison of OBSERVED facts: service/location coverage (ours vs each competitor), content gaps,
landing-page themes, messaging, and demand for competitor brands in the account's own search terms."""
import re
from collections import Counter
from urllib.parse import urlparse

THEMES = {
    "airport": ["airport", "tullamarine", "avalon", "flight"],
    "corporate": ["corporate", "executive", "business"],
    "wedding": ["wedding", "bridal"],
    "formal": ["formal", "graduation", "prom"],
    "cruise": ["cruise", "station pier", "cruise terminal"],
    "limo": ["limo", "limousine", "stretch"],
    "tours": ["tour", "winery", "wine", "yarra valley", "great ocean road", "sightseeing"],
    "events": ["event", "concert", "grand prix", "races", "mcg", "sport"],
    "hourly": ["hourly", "by the hour", "as directed"],
}


def _has(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}s?\b", text) is not None


def dedupe_terms(terms: list[str]) -> list[str]:
    out, seen = [], set()
    for t in terms:
        k = t.lower().strip()
        base = k[:-1] if k.endswith("s") else k
        if k and base not in seen:
            seen.add(base)
            out.append(k)
    return out


def headline_text(page: dict) -> str:
    path = urlparse(page["url"]).path.lower().replace("-", " ").replace("_", " ").replace("/", " ")
    h1 = page["h1"] if isinstance(page.get("h1"), list) else [page.get("h1") or ""]
    return " ".join([path, page.get("title", ""), *h1]).lower()


def page_profile(page: dict, services: list[str], locations: list[str]) -> dict:
    head = headline_text(page)
    body = " ".join([head, page.get("text", ""), *page.get("h2", [])]).lower()
    return {"mentions": {t for t in services + locations if _has(body, t)},
            "dedicated": {t for t in services + locations if _has(head, t)},
            "themes": [k for k, words in THEMES.items() if any(_has(head, w) for w in words)]}


def coverage(ours: list[dict], theirs: dict[int, list[dict]], terms: list[str]) -> list[dict]:
    """ours/theirs: page profiles. Row per term: pages mentioning it + pages dedicated to it (URL/title/H1)."""
    rows = []
    for t in terms:
        row = {"term": t, "us": {"pages": sum(t in p["mentions"] for p in ours), "dedicated": sum(t in p["dedicated"] for p in ours)},
               "competitors": {cid: {"pages": sum(t in p["mentions"] for p in ps), "dedicated": sum(t in p["dedicated"] for p in ps)}
                               for cid, ps in theirs.items()}}
        rows.append(row)
    return rows


def gaps(rows: list[dict], names: dict[int, str]) -> dict:
    """Gap = a competitor has a page dedicated to it and we have none. Advantage = we do and no competitor does
    (among the pages we could read)."""
    gap, adv = [], []
    for r in rows:
        who = [names[c] for c, v in r["competitors"].items() if v["dedicated"]]
        if who and not r["us"]["dedicated"]:
            gap.append({"term": r["term"], "competitors": who, "our_mentions": r["us"]["pages"]})
        elif r["us"]["dedicated"] and not who and r["competitors"]:
            adv.append({"term": r["term"], "our_pages": r["us"]["dedicated"]})
    return {"gaps": sorted(gap, key=lambda g: -len(g["competitors"])), "advantages": adv}


def themes(pages: list[dict], profiles: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p, prof in zip(pages, profiles, strict=True):
        for t in prof["themes"]:
            out.setdefault(t, []).append(p["url"])
    return out


def messaging(pages: list[dict]) -> dict:
    home = next((p for p in pages if (urlparse(p["url"]).path.rstrip("/") or "/") == "/"), pages[0] if pages else None)
    ctas = Counter(c for p in pages for c in p.get("ctas", []))
    return {"home_title": home.get("title", "") if home else "", "home_h1": home.get("h1", []) if home else [],
            "home_description": home.get("meta_description", "") if home else "",
            "headlines": list(dict.fromkeys(h for p in pages for h in p.get("h1", [])))[:15],
            "ctas": [c for c, _ in ctas.most_common(8)],
            "prices": list(dict.fromkeys(x for p in pages for x in p.get("prices", [])))[:12],
            "trust": sorted({t for p in pages for t in p.get("trust", [])})}


def brand_terms(name: str, domain: str, extra: list[str]) -> list[str]:
    root = domain.lower().removeprefix("www.").split(".")[0]
    terms = {name.lower().strip(), *(e.lower().strip() for e in extra)}
    if len(root) >= 4:
        terms.add(root)
    return sorted(t for t in terms if len(t) >= 3)


def search_demand(terms: list[dict], brands: list[str]) -> dict:
    """The account's OWN search terms that mention the competitor's brand (not their Ads data)."""
    squash = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())  # noqa: E731
    keys = [squash(b) for b in brands if squash(b)]
    hits = [t for t in terms if any(k in squash(t["search_term"]) for k in keys)]
    return {"terms": len(hits), "impressions": sum(t["impressions"] for t in hits), "clicks": sum(t["clicks"] for t in hits),
            "cost": round(sum(t["cost"] for t in hits), 2), "conversions": round(sum(t["conversions"] for t in hits), 2),
            "top": [{"search_term": t["search_term"], "impressions": t["impressions"], "clicks": t["clicks"], "cost": t["cost"]}
                    for t in sorted(hits, key=lambda t: (-t["impressions"], -t["clicks"]))[:10]]}
