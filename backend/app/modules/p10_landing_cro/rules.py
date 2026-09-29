"""P10 — pure landing-page checks: intent match (keywords/ads vs page), CTA, booking form, trust, mobile, speed, tracking.
Every finding carries evidence and a concrete recommendation. Score = 100 minus severity weights (floor 0)."""
import re
from dataclasses import asdict, dataclass

WEIGHT = {"critical": 20, "warning": 8, "info": 2}
CATEGORIES = ["tracking", "intent", "cta", "form", "trust", "mobile", "speed", "technical"]
STOP = {"the", "and", "for", "in", "a", "an", "to", "of", "near", "me", "my", "with", "best", "cheap", "service", "services",
        "hire", "car", "cars", "melbourne", "vic", "australia", "online", "company", "companies", "book", "booking"}
GENERIC_SUBMIT = {"submit", "send", "go", "ok", "next"}


@dataclass
class Finding:
    code: str
    category: str
    severity: str
    title: str
    detail: str
    recommendation: str
    evidence: list

    def to_dict(self) -> dict:
        return asdict(self)


def tokens(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) < 3 or w in STOP:
            continue
        out.add(w[:-1] if len(w) > 4 and w.endswith("s") else w)
    return out


def coverage(keywords: list[dict], page_text: str) -> tuple[float | None, list[dict]]:
    """Click-weighted share of keywords whose core words all appear on the page. Returns (share, uncovered top keywords)."""
    page = tokens(page_text)
    rows, total, hit = [], 0.0, 0.0
    for k in keywords:
        core = tokens(k["text"])
        if not core:
            continue
        w = max(k.get("clicks", 0), 0) + 1  # +1 so zero-click keywords still count a little
        ok = core <= page
        total += w
        hit += w if ok else 0
        if not ok:
            rows.append({"text": k["text"], "clicks": k.get("clicks", 0), "missing": sorted(core - page)})
    if not total:
        return None, []
    return round(hit / total, 3), sorted(rows, key=lambda r: -r["clicks"])[:10]


def check(page: dict, sig: dict | None, ctx: dict, *, locations: list[str], tracking_issues: list[str] | None) -> list[Finding]:
    """page: fetch result; sig: CroSignals dict (None if the page failed); ctx: ads/keywords/spend for this URL;
    tracking_issues: P06 critical issues for the page's domain, None when the domain is not a linked website."""
    f: list[Finding] = []

    def add(code, cat, sev, title, detail, rec, evidence=None):
        f.append(Finding(code, cat, sev, title, detail, rec, evidence or []))

    if sig is None or not page.get("status_code") or page["status_code"] >= 400:
        add("page_not_loading", "technical", "critical", "Landing page does not load",
            page.get("error") or f"HTTP {page.get('status_code')}", "Fix the page or point the ads to a working URL — every click here is wasted.",
            [["Ads using this URL", str(len(ctx.get("ads", [])))], ["Cost (90 days)", f"AUD {ctx.get('cost', 0):.2f}"]])
        return f
    if page.get("final_url") and page["final_url"].rstrip("/") != page["url"].rstrip("/"):
        add("redirects", "technical", "info", "Ad URL redirects", f"{page['url']} → {page['final_url']}",
            "Use the final URL directly in the ads — redirects add load time and can drop tracking parameters (gclid).")

    text_all = " ".join([sig["title"], *sig["h1"], *sig["h2"], sig["text"]])
    # --- tracking
    if not sig["has_ga4_or_gtm"]:
        add("no_analytics_tag", "tracking", "critical", "No Google Analytics / Tag Manager tag found",
            "The page HTML has no gtag.js (G-…) or GTM container.", "Install GA4 (or GTM) on this page so visits and bookings can be measured.")
    if tracking_issues is None:
        add("tracking_not_verified", "tracking", "info", "Conversion tracking not verified for this domain",
            "This domain is not added under Websites, so its GA4 conversion health can't be checked.",
            "Add the domain under Websites (with its GA4 property) or confirm its form submissions are tracked.")
    elif tracking_issues and (sig["forms"] or sig["booking_links"]):
        add("conversions_not_tracked", "tracking", "critical", "Bookings/enquiries from this page are not tracked as conversions",
            "; ".join(tracking_issues[:3]),
            "Fire a GA4 event (e.g. generate_lead / booking_submitted) on successful form submission, mark it as a key event and import it into Google Ads.",
            [[t, "P06 tracking health"] for t in tracking_issues[:3]])
    if not sig["has_ads_tag"]:
        add("no_ads_tag", "tracking", "info", "No Google Ads tag on the page",
            "Fine if conversions are imported from GA4; otherwise Google Ads cannot see conversions.",
            "Either import GA4 key events into Google Ads, or add the Google Ads conversion tag.")
    # --- intent
    kws = ctx.get("keywords", [])
    share, uncovered = coverage(kws, text_all)
    top_tokens = set().union(*(tokens(k["text"]) for k in sorted(kws, key=lambda k: -k.get("clicks", 0))[:5])) if kws else set()
    if not sig["h1"]:
        add("no_h1", "intent", "warning", "No main heading (H1)", "Visitors can't instantly see they are in the right place.",
            "Add one clear H1 that repeats the service people searched for, e.g. “Melbourne Airport Chauffeur Transfers”.")
    elif top_tokens and not (tokens(" ".join(sig["h1"])) & top_tokens):
        add("h1_intent_mismatch", "intent", "warning", "Main heading doesn't match what people searched",
            f"H1: “{sig['h1'][0][:120]}”", "Rewrite the H1 around the top keywords of the ad groups sending traffic here.",
            [["Top keywords", ", ".join(k["text"] for k in sorted(kws, key=lambda k: -k.get("clicks", 0))[:5])]])
    if share is not None and share < 0.5:
        add("low_keyword_coverage", "intent", "critical" if share < 0.25 else "warning",
            f"Page covers only {round(share * 100)}% of the searches sending traffic",
            "Many keywords of the ad groups using this page are not mentioned on it.",
            "Add a section per main service/search (or send those ad groups to a more specific page).",
            [[u["text"], f"{u['clicks']} clicks · missing: {', '.join(u['missing'])}"] for u in uncovered[:8]])
    headline_tokens = tokens(" ".join(h for a in ctx.get("ads", []) for h in a.get("headlines", [])))
    if headline_tokens and not (headline_tokens & tokens(" ".join([sig["title"], *sig["h1"]]))):
        add("ad_message_mismatch", "intent", "warning", "Ad headlines and page headline don't match",
            "People click an ad promise and land on a page that says something else.",
            "Repeat the ad's main promise (service + area) in the page title/H1.")
    if locations and not any(loc.lower() in text_all.lower() for loc in locations):
        add("no_location", "intent", "warning", "Service area not mentioned", "None of your service locations appear on the page.",
            f"Mention the areas you serve (e.g. {', '.join(locations[:3])}).")
    # --- CTA / form
    has_booking = bool(sig["forms"] or sig["booking_links"])
    if not sig["ctas"]:
        add("no_cta", "cta", "critical", "No clear call to action", "No button or link like “Book now”, “Get a quote” or “Call”.",
            "Add a prominent primary CTA (e.g. “Get an instant quote”) near the top and repeat it down the page.")
    elif not sig["early_cta"]:
        add("cta_not_early", "cta", "warning", "Call to action is not near the top", "The first CTA appears after the opening content.",
            "Place the main CTA (and phone number) in the first screen, above the fold.", [["CTAs found", ", ".join(sig["ctas"][:6])]])
    if not has_booking:
        add("no_booking_path", "form", "critical", "No way to book or request a quote on the page",
            "No form and no link to a booking/quote page.", "Add a short quote form or a clear link to the booking page.")
    for i, form in enumerate(sig["forms"][:3]):
        n = len(form["fields"])
        if n > 8:
            add("long_form", "form", "warning", f"Form {i + 1} has {n} fields", "Long forms lose enquiries, especially on mobile.",
                "Ask only for what's needed for a quote (pickup, drop-off, date/time, name, phone/email); collect the rest later.",
                [["Fields", ", ".join(x["name"] for x in form["fields"][:15])]])
        if form.get("submit_text", "").strip().lower() in GENERIC_SUBMIT:
            add("generic_submit", "form", "info", f"Form {i + 1} button says “{form['submit_text']}”", "Generic labels convert worse.",
                "Use a specific label such as “Get my quote” or “Check availability”.")
    # --- trust
    trust = sig["trust"]
    if not any(trust.values()):
        add("no_trust", "trust", "warning", "No trust signals found", "No reviews, experience, accreditation or guarantees mentioned.",
            "Add Google reviews/testimonials, years in business, licensing/insurance and a service guarantee.")
    else:
        if not trust.get("reviews"):
            add("no_reviews", "trust", "warning", "No reviews or testimonials", "Chauffeur buyers look for social proof before booking.",
                "Show your Google rating and 3–5 short testimonials near the form.")
        if not trust.get("accreditation"):
            add("no_accreditation", "trust", "info", "Licensing/insurance not mentioned", "",
                "Mention accreditation (e.g. Safe Transport Victoria), insurance and ABN.")
    if not sig["prices"]:
        add("no_prices", "trust", "info", "No indicative prices", "Visitors can't tell if you're in budget before enquiring.",
            "Show “from $…” prices or fixed-price examples (e.g. CBD → airport).")
    # --- mobile
    if not sig["viewport"]:
        add("no_viewport", "mobile", "critical", "Page is not set up for mobile", "No responsive viewport meta tag.",
            "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> and check the layout on a phone.")
    if not sig["tel_links"]:
        add("no_click_to_call", "mobile", "warning", "No click-to-call phone link", "Mobile visitors can't tap to call.",
            "Add a tel: link (ideally a sticky call button on mobile).")
    # --- speed
    ms = page.get("elapsed_ms")
    if ms and ms > 2500:
        add("slow_response", "speed", "warning", f"Server responded slowly ({ms / 1000:.1f}s)", "Measured from our server; real load time is longer.",
            "Check hosting/caching; aim for under 1s server response. Run Google PageSpeed Insights for the full picture.")
    elif ms and ms > 1500:
        add("slowish_response", "speed", "info", f"Server response {ms / 1000:.1f}s", "", "Enable page caching / a CDN.")
    if sig["html_bytes"] > 1_500_000 or sig["scripts"] > 40:
        add("heavy_page", "speed", "info", "Heavy page", f"{sig['html_bytes'] // 1024} KB HTML, {sig['scripts']} scripts.",
            "Remove unused plugins/scripts and defer non-essential ones.")
    # --- technical / content
    if not sig["meta_description"]:
        add("no_meta_description", "technical", "info", "No meta description", "", "Add a 140–160 character description with service + area.")
    if sig["images_without_alt"] > 5:
        add("images_no_alt", "technical", "info", f"{sig['images_without_alt']} images without alt text", "", "Add short descriptive alt text.")
    if sig["word_count"] < 250:
        add("thin_content", "intent", "info", f"Very little text ({sig['word_count']} words)", "",
            "Explain the service, areas, fleet and how booking works.")
    if ctx.get("cost", 0) >= 50 and ctx.get("conversions", 0) == 0:
        add("spend_no_conversions", "tracking", "warning", f"AUD {ctx['cost']:.0f} spent with 0 recorded conversions (90 days)",
            "Either the page does not convert or conversions are not tracked (see tracking findings).",
            "Fix tracking first, then the page issues above.", [["Clicks", str(ctx.get("clicks", 0))]])
    return f


def score(findings: list[Finding]) -> int:
    if any(x.code == "page_not_loading" for x in findings):
        return 0
    return max(0, 100 - sum(WEIGHT[x.severity] for x in findings))
