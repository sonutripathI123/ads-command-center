"""P15 — campaign structure builder. Pure functions: theme clustering, match types, landing-page choice,
negatives, default settings and the launch checklist. Nothing here talks to Google Ads."""
import re
from dataclasses import dataclass

# Order matters: first matching theme wins (airport before generic chauffeur, etc.).
THEMES: list[tuple[str, str, list[str]]] = [
    ("airport", "Airport Transfers", ["airport", "tullamarine", "avalon", "terminal", "flight", "arrivals", "pickup", "pick up"]),
    ("wedding", "Weddings & Formals", ["wedding", "bridal", "bride", "formal", "school formal", "prom", "debutante"]),
    ("cruise", "Cruise & Port Transfers", ["cruise", "port melbourne", "station pier", "ship"]),
    ("limo", "Limousine Hire", ["limo", "limousine", "stretch", "hummer"]),
    ("tours", "Tours & Hourly Hire", ["tour", "winery", "wineries", "yarra valley", "mornington", "hourly", "by the hour", "day trip"]),
    ("events", "Events & Special Occasions", ["event", "concert", "races", "grand prix", "mcg", "sport", "party", "birthday", "funeral"]),
    ("corporate", "Corporate & Executive", ["corporate", "executive", "business", "company", "roadshow", "meeting", "conference", "vip"]),
    ("chauffeur", "Chauffeur Service", ["chauffeur", "chauffeured", "chauffer", "private driver", "driver", "car service", "private car",
                                       "hire car", "sedan", "luxury car", "car hire", "people mover", "van"]),
]
THEME_BY_KEY = {k: (label, words) for k, label, words in THEMES}
# A "rental" keyword that also asks for a driver is a chauffeur customer, not a self-drive renter.
DRIVER_WORDS = ["chauffeur", "chauffeured", "chauffer", "driver", "driven", "with driver"]
RENTAL_WORDS = ["rental", "rent", "renting"]
# Self-drive rental brands: people searching these want to drive themselves, not a chauffeur.
RENTAL_BRANDS = ["europcar", "hertz", "avis", "budget car", "budget rent", "thrifty", "sixt", "enterprise rent", "redspot",
                 "east coast car", "bayswater car rental", "apex car rental", "jucy", "turo", "car next door"]


def _has(word: str, text: str) -> bool:
    return re.search(r"(?<![\w])" + re.escape(word) + r"(?![\w])", text) is not None


def _has_word(word: str, text: str) -> bool:
    """Whole-word match that also accepts a plural -s ('limos', 'chauffeurs', 'drivers')."""
    return re.search(r"(?<![\w])" + re.escape(word) + r"s?(?![\w])", text) is not None


def theme_of(keyword: str) -> str | None:
    t = keyword.lower()
    for key, _, words in THEMES:
        if any(_has_word(w, t) for w in words):
            return key
    return None


@dataclass
class Kw:
    text: str
    match_type: str
    cost: float = 0.0
    clicks: int = 0
    conversions: float = 0.0
    source: str = ""


def cluster(keywords: list[dict], values: dict[str, str], themes: list[str] | None = None) -> tuple[dict[str, list[Kw]], list[Kw], list[dict]]:
    """keywords: P05 rows. values: P08 business value per keyword text.
    → (theme → keywords, unassigned, negatives found among keywords)."""
    groups: dict[str, list[Kw]] = {}
    unassigned: list[Kw] = []
    negatives: list[dict] = []
    seen: set[str] = set()
    for k in sorted(keywords, key=lambda k: (-k["conversions"], -k["clicks"], k["text"])):
        text = " ".join(k["text"].lower().split())
        if not text or text in seen:
            continue
        seen.add(text)
        brand = next((b for b in RENTAL_BRANDS if _has(b, text)), None)
        if brand:
            negatives.append({"text": brand, "match_type": "PHRASE",
                              "reason": f"'{brand}' is a self-drive rental brand (from keyword '{text}')"})
            continue
        rental_with_driver = any(_has(w, text) for w in RENTAL_WORDS) and any(_has(w, text) for w in DRIVER_WORDS) \
            and not any(_has(w, text) for w in ("job", "jobs", "career", "salary", "course", "cheap", "free"))
        if values.get(text) == "negative" and not rental_with_driver:
            negatives.append({"text": text, "match_type": "PHRASE",
                              "reason": f"keyword '{text}' matches your 'never want' rules or a place you don't serve"})
            continue
        mt = "EXACT" if k["conversions"] > 0 else "PHRASE"
        kw = Kw(text, mt, k["cost"], k["clicks"], k["conversions"], k.get("ad_group_name", ""))
        key = theme_of(text)
        if key and (themes is None or key in themes):
            groups.setdefault(key, []).append(kw)
        else:
            unassigned.append(kw)
    uniq = {(n["text"], n["match_type"]): n for n in negatives}
    return groups, unassigned, list(uniq.values())


# Words that must appear in a page URL for it to count as that theme's page. The generic chauffeur theme
# always uses the homepage (suburb or niche pages such as "baby seat" are too specific).
PRIMARY = {"airport": ["airport"], "wedding": ["wedding", "formal"], "cruise": ["cruise"], "limo": ["limo", "limousine"],
           "tours": ["tour", "winery", "wineries"], "events": ["event", "events"],
           "corporate": ["corporate", "executive", "business"], "chauffeur": []}


def best_landing_page(theme: str, pages: list[dict], base_url: str) -> tuple[str, int, str]:
    """→ (url, score 0–100, why). pages: P03 website_pages rows."""
    home = base_url.rstrip("/") + "/"
    if not PRIMARY.get(theme):
        return home, 60, "homepage (general chauffeur theme)"
    _, words = THEME_BY_KEY[theme]
    best = (home, 10, "homepage (no page matched this theme)")
    for p in pages:
        if (p.get("status_code") or 0) >= 400 or "http_error" in p.get("issues", []):
            continue
        path = p["url"].lower().split("://", 1)[-1].split("/", 1)[-1]
        if not any(w in path for w in PRIMARY[theme]):
            continue
        s, why = 50, ["URL matches theme"]
        head = f"{p.get('title', '')} {p.get('h1', '')}".lower()
        if any(_has(w, head) for w in words):
            s += 25
            why.append("title/H1 match")
        if p.get("cta_count"):
            s += 10
        if p.get("has_form") or p.get("has_phone"):
            s += 10
        s -= 5 * len([i for i in p.get("issues", []) if i in ("slow", "thin_content", "no_cta")])
        s -= min(10, path.count("-"))  # prefer short, general pages over long niche URLs
        if s > best[1]:
            best = (p["url"], min(100, s), ", ".join(why))
    return best


def default_negatives(excluded_terms: list[str], other_locations: list[str]) -> list[dict]:
    out = [{"text": t, "match_type": "PHRASE", "reason": "on your 'never want' list"} for t in excluded_terms]
    out += [{"text": t, "match_type": "PHRASE", "reason": "place you don't serve"} for t in other_locations]
    return out


def default_settings(*, daily_budget: float, max_cpc: float, tracking_ok: bool, locations: list[str]) -> dict:
    return {
        "type": "SEARCH", "status": "PAUSED", "networks": {"google_search": True, "search_partners": False, "display": False},
        "daily_budget": round(daily_budget, 2), "currency": "AUD",
        "bidding": ({"strategy": "MAXIMIZE_CONVERSIONS"} if tracking_ok else {"strategy": "MAXIMIZE_CLICKS", "max_cpc": round(max_cpc, 2)}),
        "bidding_reason": ("Conversion tracking looks healthy." if tracking_ok else
                           "Conversion tracking isn't reliable yet, so clicks are bought with a CPC cap until real enquiries are recorded."),
        "locations": locations[:25], "location_option": "PRESENCE", "languages": ["en"], "ad_schedule": "all day",
    }


def checklist(*, tracking_critical: list[str], landing: list[dict], ad_groups: list[dict], negatives: int,
              settings: dict) -> list[dict]:
    """Each item: {key, label, status: pass|fail|manual, detail}."""
    items = []
    add = lambda key, label, ok, detail: items.append({"key": key, "label": label, "status": ok, "detail": detail})  # noqa: E731
    add("tracking", "Conversion tracking records real enquiries",
        "fail" if tracking_critical else "pass", "; ".join(tracking_critical) or "no critical tracking issues (P06)")
    broken = [lp for lp in landing if lp in ("broken",)]
    add("landing_pages", "Every ad group has a working landing page on your site",
        "pass" if ad_groups and all(g.get("final_url") for g in ad_groups) and not broken else "fail",
        f"{sum(1 for g in ad_groups if g.get('final_url'))}/{len(ad_groups)} ad groups have a landing page")
    approved = sum(1 for g in ad_groups if g.get("ad_status") == "approved")
    add("ads", "Each ad group has an approved ad", "pass" if ad_groups and approved == len(ad_groups) else "fail",
        f"{approved}/{len(ad_groups)} approved (write and approve them on this page / Ads & Assets)")
    add("keywords", "Each ad group has keywords", "pass" if ad_groups and all(g["keywords"] for g in ad_groups) else "fail",
        f"{sum(len(g['keywords']) for g in ad_groups)} keywords in {len(ad_groups)} ad groups")
    add("negatives", "Negative keywords added", "pass" if negatives else "fail", f"{negatives} negatives")
    add("budget", "Daily budget set", "pass" if settings.get("daily_budget", 0) > 0 else "fail",
        f"AUD {settings.get('daily_budget', 0):,.2f}/day")
    add("location", "Location targeting = people IN your areas", "manual",
        "In Google Ads Editor set Location options → 'Presence: people in or regularly in your targeted locations'")
    add("conversion_action", "Only the real enquiry is a Primary conversion", "manual",
        "Google Ads → Goals → Conversions: set the GA4 enquiry event as Primary, others Secondary")
    return items
