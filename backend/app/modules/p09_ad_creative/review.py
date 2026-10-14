"""P09 — plain-language suggestions for an existing ad, from its strength, rule checks and performance.
Pure functions. Honest by design: with too little data it says so instead of judging."""

MIN_IMPRESSIONS = 500   # below this, CTR is noise
MIN_CLICKS = 10         # below this, "no conversions" is noise
MIN_WASTED_COST = 20.0  # spend without a conversion before an ad is called out


def benchmark(rows: list[dict]) -> dict:
    """Account-wide CTR and cost per conversion across the ads that have data (the yardstick for each ad)."""
    impr = sum(r["impressions"] or 0 for r in rows)
    clicks = sum(r["clicks"] or 0 for r in rows)
    cost = sum(r["cost"] or 0 for r in rows)
    conv = sum(r["conversions"] or 0 for r in rows)
    return {"ctr": clicks / impr if impr else None, "cpa": cost / conv if conv else None}


def suggest(r: dict, bench: dict) -> list[str]:
    out: list[str] = []
    errs = [f for f in r.get("findings", []) if f["severity"] == "error"]
    warns = [f for f in r.get("findings", []) if f["severity"] == "warning"]
    if errs:
        out.append(f"Fix {len(errs)} error(s) first, Google would reject or limit them: " + "; ".join(sorted({f['message'] for f in errs})[:3]))
    if len(r["headlines"]) < 15:
        out.append(f"Add {15 - len(r['headlines'])} more headline(s). 15 gives Google the most combinations to test.")
    if len(r["descriptions"]) < 4:
        out.append(f"Add {4 - len(r['descriptions'])} more description(s) (4 is the maximum).")
    if warns:
        out.append(f"Review {len(warns)} warning(s): " + "; ".join(sorted({f['message'] for f in warns})[:3]))
    if r["strength"] < 60:
        out.append(f"Estimated ad strength is low ({r['strength']}/100). Use \"Improve with AI\" to write a stronger version.")
    impr, clicks, cost, conv, ctr = r["impressions"] or 0, r["clicks"] or 0, r["cost"] or 0.0, r["conversions"] or 0.0, r["ctr"]
    if impr == 0:
        out.append("No impressions in this period (paused or new), so performance cannot be judged yet. Fix the points above before enabling.")
    else:
        if conv == 0 and clicks >= MIN_CLICKS and cost >= MIN_WASTED_COST:
            out.append(f"Spent ${cost:,.0f} on {clicks} clicks with no conversion. Check the landing page and the search terms, "
                       "and make the call to action clearer.")
        if ctr is not None and bench.get("ctr") and impr >= MIN_IMPRESSIONS and ctr < 0.6 * bench["ctr"]:
            out.append(f"CTR {ctr * 100:.1f}% is well below the account's {bench['ctr'] * 100:.1f}%. The headlines may not match what people search for.")
        if conv > 0 and bench.get("cpa"):
            cpa = cost / conv
            if cpa > 1.5 * bench["cpa"]:
                out.append(f"Cost per conversion ${cpa:,.0f} is more than 50% above the account's ${bench['cpa']:,.0f}. Rework or pause it.")
            elif cpa < 0.7 * bench["cpa"]:
                out.append(f"Converts cheaper (${cpa:,.0f}) than the account's ${bench['cpa']:,.0f}. Keep it, and use its angles for new ads.")
        if conv and conv < 3:
            out.append("Only a few conversions so far, so treat any verdict as a hint, not proof.")
    return out or ["Nothing urgent. Keep it running and re-check when there is more data."]
