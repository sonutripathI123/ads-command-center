"""P09 — "Smart ad copy" context. Pure functions: what worked, what didn't, which search terms converted and which lines
were written or run recently, turned into extra briefing text for the writer. No DB or network here (service.py feeds it).
Honest by design: small samples are flagged as hints, and no number from this section may be quoted in an ad."""

GOALS = {
    "conversions": "get more conversions (quote requests and bookings)",
    "clicks": "get more qualified clicks at a low cost per click",
    "cpa": "lower the cost per conversion",
}
MIN_CLICKS = 10          # fewer clicks than this is noise for ranking ads
LOSER_MIN_COST = 20.0    # an ad is only "weak" once it has spent this much without a conversion
MAX_PER_BUCKET = 3
MAX_TERMS = 12
MAX_AVOID_HEADLINES = 45
MAX_AVOID_DESCRIPTIONS = 12


def _is_rsa(a: dict) -> bool:
    return a.get("type") == "RESPONSIVE_SEARCH_AD" and bool(a.get("headlines"))


def _cpa(a: dict) -> float:
    return a["cost"] / a["conversions"] if a.get("conversions") else float("inf")


def split_ads(ads: list[dict], goal: str) -> tuple[list[dict], list[dict]]:
    """→ (winners, losers) for the goal, at most MAX_PER_BUCKET each."""
    rsa = [a for a in ads if _is_rsa(a)]
    if goal == "clicks":
        ranked = [a for a in rsa if (a.get("clicks") or 0) >= MIN_CLICKS and a.get("ctr") is not None]
        winners = sorted(ranked, key=lambda a: -a["ctr"])[:MAX_PER_BUCKET]
        losers = [a for a in sorted(ranked, key=lambda a: a["ctr"]) if a not in winners and (a.get("impressions") or 0) >= 200][:MAX_PER_BUCKET]
        return winners, losers
    converted = [a for a in rsa if (a.get("conversions") or 0) > 0]
    key = (lambda a: _cpa(a)) if goal == "cpa" else (lambda a: (-a["conversions"], _cpa(a)))
    winners = sorted(converted, key=key)[:MAX_PER_BUCKET]
    weak = [a for a in rsa if (a.get("conversions") or 0) == 0 and (a.get("clicks") or 0) >= MIN_CLICKS and (a.get("cost") or 0) >= LOSER_MIN_COST]
    return winners, sorted(weak, key=lambda a: -a["cost"])[:MAX_PER_BUCKET]


def converted_terms(terms: list[dict]) -> list[dict]:
    got = [t for t in terms if (t.get("conversions") or 0) > 0]
    return sorted(got, key=lambda t: (-t["conversions"], t.get("cost") or 0))[:MAX_TERMS]


def avoid_lines(recent: list[dict]) -> tuple[list[str], list[str]]:
    """recent = draft dicts (headlines/descriptions) and/or running ads. Unique, order kept, capped."""
    hs: dict[str, str] = {}
    ds: dict[str, str] = {}
    for r in recent:
        for h in r.get("headlines", []):
            if h.strip():
                hs.setdefault(h.strip().lower(), h.strip())
        for d in r.get("descriptions", []):
            if d.strip():
                ds.setdefault(d.strip().lower(), d.strip())
    return list(hs.values())[:MAX_AVOID_HEADLINES], list(ds.values())[:MAX_AVOID_DESCRIPTIONS]


def _ad_line(a: dict) -> str:
    cpa = f", cost per conversion {a['cost'] / a['conversions']:.0f} AUD" if a.get("conversions") else ""
    ctr = f"{a['ctr'] * 100:.1f}%" if a.get("ctr") is not None else "n/a"
    return (f"- Ad group '{a.get('ad_group_name', '')}': {a.get('clicks', 0)} clicks, CTR {ctr}, {a.get('conversions', 0):g} conversions, "
            f"cost {a.get('cost', 0):.0f} AUD{cpa}\n  Headlines: {' | '.join(a['headlines'][:8])}\n  Descriptions: {' | '.join(a['descriptions'][:2])}")


def build(goal: str, winners: list[dict], losers: list[dict], terms: list[dict], avoid_h: list[str], avoid_d: list[str]) -> tuple[str, dict]:
    """→ (briefing text appended to the writer prompt, summary counts for the draft notes)."""
    goal = goal if goal in GOALS else "conversions"
    parts = [f"Goal of this ad: {GOALS[goal]}. Write copy that serves this goal."]
    if winners or losers or terms:
        parts.append("PAST PERFORMANCE (last 90 days). These samples are small, so treat them as hints, not proof. "
                     "Never quote any number from this section in the ad.")
    if winners:
        parts.append("Ads that worked best for this goal (reuse their ANGLES and themes, never copy lines word for word):\n" +
                     "\n".join(_ad_line(a) for a in winners))
    if losers:
        parts.append("Ads that spent money without results (avoid their angles):\n" + "\n".join(_ad_line(a) for a in losers))
    if terms:
        parts.append("Search terms that led to conversions (work the intent behind them into headlines where natural):\n" +
                     "\n".join(f"- {t['search_term']} ({t['conversions']:g} conv, {t.get('cost', 0):.0f} AUD)" for t in terms))
    if avoid_h or avoid_d:
        parts.append("RECENTLY WRITTEN OR RUN COPY: do NOT reuse any of these lines and do not write close paraphrases. "
                     "Take clearly different angles and wording this time.\n"
                     + ("Headlines: " + " | ".join(avoid_h) + "\n" if avoid_h else "")
                     + ("Descriptions: " + " | ".join(avoid_d) if avoid_d else ""))
    summary = {"goal": goal, "winners": len(winners), "losers": len(losers), "terms": len(terms),
               "avoided": len(avoid_h) + len(avoid_d)}
    return "\n\n".join(parts), summary


def repeat_count(headlines: list[str], descriptions: list[str], avoid_h: list[str], avoid_d: list[str]) -> int:
    """How many generated lines are identical (ignoring case) to a line we asked to avoid."""
    ah, ad = {x.lower() for x in avoid_h}, {x.lower() for x in avoid_d}
    return sum(h.strip().lower() in ah for h in headlines) + sum(d.strip().lower() in ad for d in descriptions)


def note(summary: dict | None, mode: str, repeats: int) -> str:
    if summary is None:
        return ""
    base = (f"Smart ad copy — goal: {summary['goal']}; used {summary['winners']} best ad(s), {summary['losers']} weak ad(s), "
            f"{summary['terms']} converting search term(s); avoided {summary['avoided']} recent line(s).")
    if mode != "live":
        return base + " Template mode cannot learn from this history — switch on live Claude for real learning."
    if not (summary["winners"] or summary["losers"] or summary["terms"] or summary["avoided"]):
        return base + " No history found yet, so this ad was written from keywords and rules only."
    return base + (f" {repeats} line(s) still repeat earlier copy — edit them." if repeats else " No repeated lines.")
