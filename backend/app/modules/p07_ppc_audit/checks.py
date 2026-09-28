"""P07 — audit checks. Pure functions over plain data gathered from P03/P05/P06/P08/P21 interfaces.

Each issue follows the MID §18 recommendation contract (observation, evidence, reasoning, proposed action,
expected impact, confidence, risk) so P14 can later adopt it unchanged. Observation = measured facts only;
reasoning = our interpretation. Nothing here changes Google Ads.
"""
from collections import defaultdict
from dataclasses import dataclass, field

SMART_BIDDING = {"MAXIMIZE_CONVERSIONS", "TARGET_CPA", "MAXIMIZE_CONVERSION_VALUE", "TARGET_ROAS"}
SEVERITY_WEIGHT = {"critical": 15, "warning": 5, "info": 1}


@dataclass
class Issue:
    code: str
    category: str      # tracking | account | bidding | keywords | search_terms | ads | landing_pages | organic
    severity: str      # critical | warning | info
    title: str
    observation: str
    evidence: list[tuple[str, str]]
    reasoning: str
    action: str
    impact: str
    confidence: float
    risk: str          # risk of making the proposed change: low | medium | high
    entity_type: str = "account"
    entity_id: str = ""
    link: str | None = None  # dashboard page with details


@dataclass
class AuditData:
    currency: str
    days: int
    totals: dict
    campaigns: list[dict]
    ad_groups: list[dict]
    keywords: list[dict]
    search_terms: list[dict]
    ads: list[dict]
    term_values: dict[str, str]           # search term → business value (P08 classifier)
    rules: object                          # P21 Rules
    website: object | None = None          # P03 WebsiteRef
    tracking: list[dict] = field(default_factory=list)       # P06 health items
    landing_pages: list[dict] = field(default_factory=list)  # P03 landing page mappings
    pages: list[dict] = field(default_factory=list)          # P03 pages
    organic_queries: list[dict] = field(default_factory=list)


def _m(v: float, cur: str) -> str:
    return f"{cur} {v:,.2f}"


def _pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def run_checks(d: AuditData) -> list[Issue]:
    out: list[Issue] = []
    cur, t, r = d.currency, d.totals, d.rules
    min_spend = max(getattr(r, "min_spend_for_negative", 20.0), 20.0)
    enabled = [c for c in d.campaigns if c.get("status") == "ENABLED"]

    # --- account -----------------------------------------------------------------------------
    if d.campaigns and not enabled:
        out.append(Issue(
            "all_campaigns_paused", "account", "critical", "No campaign is running",
            f"All {len(d.campaigns)} campaigns are paused.",
            [("Campaigns", str(len(d.campaigns))), ("Enabled", "0"), (f"Spend, last {d.days} days", _m(t.get('cost', 0), cur))],
            "While everything is paused the account produces no paid leads. If this is deliberate (e.g. fixing tracking first) "
            "that's fine — but it should be a decision, not an accident.",
            "Confirm the pause is intentional. Fix the critical tracking issues below before re-enabling.",
            "Paid leads resume when a campaign is enabled.", 1.0, "low"))

    # --- tracking (from P06) -----------------------------------------------------------------------
    sev = {"no_key_events": "critical", "form_submit_missing": "critical", "ads_vs_ga4_conversions": "warning",
           "paid_sessions_low": "warning", "no_mapping": "warning", "no_ga4": "warning", "no_ga4_data": "warning"}
    for h in d.tracking:
        if h["code"] in sev:
            out.append(Issue(
                f"tracking_{h['code']}", "tracking", sev[h["code"]], h["title"], h["detail"], [("Source", "GA4 / Google Ads (P06)")],
                "Without reliable conversion data neither you nor Google's bidding can tell which clicks become bookings.",
                "Fix on the website / in GA4 and Google Ads conversion settings (see the Conversions page).",
                "Every other optimisation depends on this — highest leverage fix.", 0.9, "low", link="/conversions"))

    conv_ok = t.get("conversions", 0) >= max(1, t.get("clicks", 0) / 50)
    tracking_broken = any(h["code"] in ("no_key_events", "form_submit_missing") for h in d.tracking)
    smart = sorted({c["bidding_strategy_type"] for c in d.campaigns if c.get("bidding_strategy_type") in SMART_BIDDING})
    if smart and (tracking_broken or not conv_ok):
        out.append(Issue(
            "smart_bidding_on_weak_data", "bidding", "critical", "Automated bidding is learning from unreliable conversions",
            f"Campaigns use {', '.join(smart)}; the account recorded {t.get('conversions', 0):g} conversions from {t.get('clicks', 0)} clicks"
            + (" and GA4 records no enquiries." if tracking_broken else "."),
            [("Bid strategies", ", ".join(smart)), ("Conversions", f"{t.get('conversions', 0):g}"), ("Clicks", str(t.get("clicks", 0)))],
            "Smart bidding raises bids for clicks that look like past conversions. If conversions are missing or are not real "
            "enquiries, it optimises toward the wrong people.",
            "Fix conversion tracking first. Until ~30 real conversions/month, prefer Maximize Clicks with a max CPC or Manual CPC.",
            "Stops budget flowing to clicks that only look like conversions.", 0.75, "medium"))

    for c in d.campaigns:
        if c["cost"] >= max(3 * min_spend, 50) and c["conversions"] == 0:
            out.append(Issue(
                "campaign_no_conversions", "account", "warning", f"'{c['name']}' spent without a conversion",
                f"{_m(c['cost'], cur)} over {c['clicks']} clicks, 0 conversions in {d.days} days.",
                [("Cost", _m(c["cost"], cur)), ("Clicks", str(c["clicks"])), ("CTR", _pct(c["ctr"] or 0))],
                "Either tracking misses its leads or the traffic doesn't convert (targeting, ads or landing page).",
                "Check tracking first; then review its search terms and landing page.", "Frees budget or reveals hidden leads.",
                0.7, "low", "campaign", c["google_id"], "/campaigns"))
    target = getattr(r, "target_cost_per_conversion", None)
    if target:
        for c in d.campaigns:
            if c["cost_per_conversion"] and c["cost_per_conversion"] > 1.5 * target:
                out.append(Issue(
                    "campaign_above_target_cpa", "bidding", "warning", f"'{c['name']}' costs more than your target per conversion",
                    f"{_m(c['cost_per_conversion'], cur)} per conversion vs target {_m(target, cur)}.",
                    [("Cost / conv.", _m(c["cost_per_conversion"], cur)), ("Target", _m(target, cur)), ("Conversions", f"{c['conversions']:g}")],
                    "Spending above target on this campaign lowers overall profit per booking.",
                    "Lower bids/budget, tighten keywords, or improve the landing page.", "Cheaper conversions.", 0.6, "medium",
                    "campaign", c["google_id"], "/campaigns"))
    if t.get("clicks", 0) >= 100 and t.get("conv_rate") is not None and t["conv_rate"] < 0.01:
        out.append(Issue(
            "low_conversion_rate", "account", "warning", "Very low conversion rate",
            f"{_pct(t['conv_rate'])} of {t['clicks']} clicks converted.",
            [("Clicks", str(t["clicks"])), ("Conversions", f"{t.get('conversions', 0):g}"), ("Conv. rate", f"{t['conv_rate'] * 100:.2f}%")],
            "Chauffeur search campaigns usually convert several % of clicks. Below 1 % points to tracking gaps, weak landing pages "
            "or poor-fit traffic.", "Fix tracking, then compare landing pages and search terms of the best vs worst ad groups.",
            "Each +1 % conversion rate is roughly +1 lead per 100 clicks.", 0.6, "low"))

    # --- search terms / keywords ---------------------------------------------------------------------
    neg_cost = sum(s["cost"] for s in d.search_terms if s["conversions"] == 0 and d.term_values.get(s["search_term"].lower()) == "negative")
    if neg_cost > 0:
        out.append(Issue(
            "irrelevant_search_spend", "search_terms", "warning" if neg_cost >= min_spend else "info",
            "Money spent on searches you don't want", f"{_m(neg_cost, cur)} went to excluded or wrong-location searches.",
            [("Wasted", _m(neg_cost, cur))], "These searches match your 'never want' rules and brought no conversions.",
            "Review and accept the negative keyword suggestions.", f"Saves about {_m(neg_cost * 30 / max(d.days, 1), cur)} per month.",
            0.85, "low", link="/search-terms/negatives"))
    st_cost = sum(s["cost"] for s in d.search_terms)
    zero = sum(s["cost"] for s in d.search_terms if s["conversions"] == 0)
    if st_cost >= 100 and zero / st_cost > 0.6:
        out.append(Issue(
            "non_converting_search_share", "search_terms", "info", "Most search-term spend brought no conversion",
            f"{_pct(zero / st_cost)} of search-term spend ({_m(zero, cur)}) had 0 conversions.",
            [("Search-term spend", _m(st_cost, cur)), ("With 0 conversions", _m(zero, cur))],
            "Many of these are relevant searches, so this mostly reflects the tracking/landing-page problem rather than bad keywords.",
            "Fix tracking first, then re-check this share.", "Clarity on which searches really work.", 0.5, "low", link="/search-terms"))

    kw_cost = sum(k["cost"] for k in d.keywords)
    broad = [k for k in d.keywords if k.get("match_type") == "BROAD"]
    broad_cost, broad_conv = sum(k["cost"] for k in broad), sum(k["conversions"] for k in broad)
    if kw_cost > 0 and broad_cost >= 50 and broad_cost / kw_cost >= 0.3 and broad_conv == 0:
        out.append(Issue(
            "broad_match_no_conversions", "keywords", "warning", "Broad match keywords spend without converting",
            f"Broad match took {_pct(broad_cost / kw_cost)} of keyword spend ({_m(broad_cost, cur)}) with 0 conversions.",
            [("Broad keywords", str(len(broad))), ("Broad spend", _m(broad_cost, cur))],
            "Broad match relies on good conversion data to find the right searches; without it, it drifts.",
            "Switch the costliest broad keywords to phrase/exact until tracking is fixed.", "Tighter, more relevant traffic.",
            0.65, "medium", link="/keywords"))
    low_qs = [k for k in d.keywords if k.get("quality_score") is not None and k["quality_score"] <= 4 and k["impressions"] > 0]
    if len(low_qs) >= 5 or sum(k["cost"] for k in low_qs) >= 50:
        out.append(Issue(
            "low_quality_score", "keywords", "warning", f"{len(low_qs)} keywords with Quality Score ≤ 4",
            f"They spent {_m(sum(k['cost'] for k in low_qs), cur)}.", [("Examples", ", ".join(k["text"] for k in low_qs[:5]))],
            "Low Quality Score means Google charges you more per click and shows you less.",
            "Make ad text and landing page match these keywords more closely, or move them to their own ad group.",
            "Lower CPC on the same traffic.", 0.6, "low", link="/keywords/insights"))
    dup = defaultdict(set)
    en_ids = {c["google_id"] for c in enabled}
    for k in d.keywords:
        if k.get("status") == "ENABLED" and k.get("campaign_google_id") in en_ids:
            dup[(k["text"].lower(), k.get("match_type"))].add(k.get("campaign_name", ""))
    dups = {k: v for k, v in dup.items() if len(v) > 1}
    if dups:
        out.append(Issue(
            "duplicate_keywords_across_campaigns", "keywords", "info", f"{len(dups)} keywords run in more than one active campaign",
            "Same keyword + match type in several enabled campaigns.", [("Examples", ", ".join(f"{t} ({m})" for t, m in list(dups)[:5]))],
            "Your campaigns compete with each other for the same search, which muddies reporting.",
            "Keep each keyword in one campaign.", "Cleaner data, no self-competition.", 0.7, "low", link="/keywords"))
    per_group = defaultdict(int)
    for k in d.keywords:
        if k.get("status") == "ENABLED":
            per_group[k.get("ad_group_name", "")] += 1
    big = [g for g, n in per_group.items() if n > 30]
    if big:
        out.append(Issue(
            "oversized_ad_groups", "keywords", "warning" if any(per_group[g] > 100 for g in big) else "info",
            f"{len(big)} ad group(s) have more than 30 keywords",
            ", ".join(f"{g} ({per_group[g]})" for g in big[:5]), [("Ad groups", str(len(big)))],
            "Large ad groups make it hard for one ad and one landing page to match every keyword.",
            "Split by theme (e.g. airport / corporate / wedding).", "Higher relevance and Quality Score.", 0.5, "low", link="/ad-groups"))

    # --- ads -------------------------------------------------------------------------------------
    ads_by_group = defaultdict(list)
    for a in d.ads:
        if a.get("status") == "ENABLED":
            ads_by_group[a.get("ad_group_name", "")].append(a)
    no_ads = [g["name"] for g in d.ad_groups if g.get("status") == "ENABLED" and g.get("type") == "SEARCH_STANDARD" and not ads_by_group.get(g["name"])]
    if no_ads:
        out.append(Issue(
            "ad_groups_without_ads", "ads", "warning", f"{len(no_ads)} ad groups have no active ad",
            ", ".join(no_ads[:5]), [("Ad groups", str(len(no_ads)))], "An ad group without an enabled ad cannot show.",
            "Add a responsive search ad to each, or pause the ad group.", "Keywords you pay to manage actually serve.", 0.8, "low", link="/ad-groups"))
    thin = [a for a in d.ads if a.get("status") == "ENABLED" and a.get("type") == "RESPONSIVE_SEARCH_AD"
            and (len(a.get("headlines", [])) < 8 or len(a.get("descriptions", [])) < 3)]
    if thin:
        out.append(Issue(
            "thin_responsive_ads", "ads", "warning", f"{len(thin)} responsive search ads have too few headlines/descriptions",
            "Fewer than 8 headlines or 3 descriptions.", [("Ads", str(len(thin))),
                                                          ("Example", f"{thin[0].get('ad_group_name', '')}: {len(thin[0].get('headlines', []))} headlines")],
            "Google tests combinations; more distinct assets usually means better ad strength and CTR.",
            "Add up to 15 headlines (service, area, trust, price, call to action) and 4 descriptions.", "Higher CTR and Ad Strength.",
            0.6, "low"))

    # --- landing pages (P03) ------------------------------------------------------------------------
    if d.website is None:
        out.append(Issue("no_website_linked", "landing_pages", "info", "No website linked to this Google Ads account",
                         "Landing pages and GA4 can't be checked.", [], "Audit can't see what happens after the click.",
                         "Link the account on the Websites page.", "Enables landing-page and tracking checks.", 1.0, "low", link="/websites"))
    for lp in d.landing_pages:
        if lp["status"] == "broken":
            out.append(Issue(
                "landing_page_broken", "landing_pages", "critical", "Ads send people to a broken page", lp["final_url"],
                [("Ads", str(lp["ads"])), ("Used by", "; ".join(lp["ad_groups"][:3]))], "Every click on these ads is paid and wasted.",
                "Fix the page or change the ads' final URL.", "Stops 100 % waste on these ads.", 0.95, "low",
                "landing_page", lp["final_url"], "/websites"))
        elif lp["status"] == "other_domain":
            out.append(Issue(
                "landing_page_other_domain", "landing_pages", "warning", "Ads send people to a different website", lp["final_url"],
                [("Ads", str(lp["ads"])), ("Used by", "; ".join(lp["ad_groups"][:3])),
                 ("This account's site", getattr(d.website, "domain", "?"))],
                "Leads from these ads land on another brand's site and won't show in this site's GA4 or bookings.",
                "Confirm it's intended; otherwise point them to this website.", "Correct attribution per brand.", 0.8, "low",
                "landing_page", lp["final_url"], "/websites"))
    ad_pages = {lp["page_id"] for lp in d.landing_pages if lp.get("page_id")}
    weak = [p for p in d.pages if p["id"] in ad_pages and set(p["issues"]) & {"no_cta", "no_form_or_phone", "slow", "thin_content", "http_error"}]
    for p in weak:
        out.append(Issue(
            "landing_page_weak", "landing_pages", "warning", "An ad landing page is missing key elements", p["url"],
            [("Problems", ", ".join(i.replace("_", " ") for i in p["issues"]))],
            "Paid visitors need an obvious way to book or call within seconds.",
            "Add a clear 'Get a quote' button, visible phone number and short form above the fold; speed the page up.",
            "Higher conversion rate from the same clicks.", 0.6, "low", "landing_page", p["url"], "/websites"))

    # --- organic context (P06 Search Console) -----------------------------------------------------------
    brand = [b for b in (getattr(r, "brand_terms", []) or [])] or ([d.website.name.lower()] if d.website else [])
    for q in d.organic_queries:
        if q["query"].lower() in brand and q["position"] > 10 and q["impressions"] >= 50:
            out.append(Issue(
                "brand_ranks_poorly", "organic", "info", f"Your brand search '{q['query']}' is not on Google's first page",
                f"Average organic position {q['position']} ({q['impressions']} impressions, {q['clicks']} clicks).",
                [("Position", str(q["position"]))], "People searching for you by name may not find your site for free.",
                "Keep a small brand campaign running and work on brand SEO (Google Business Profile, homepage title).",
                "Protects leads from people already looking for you.", 0.6, "low", link="/conversions"))
            break

    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(out, key=lambda i: (order[i.severity], -i.confidence))


def score(issues: list[Issue]) -> int:
    return max(0, 100 - sum(SEVERITY_WEIGHT[i.severity] for i in issues))
