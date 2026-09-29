"""P11 — INTERPRETATION of observed facts (kept separate from the observations). Live: Claude via the official
`anthropic` SDK with a strict JSON schema (same safety pattern as P09/P10/P14). Template: rule-based from the gaps.
Every point cites evidence keys (obs:<id>, gap:<term>, demand:<competitor>); unknown keys are dropped."""
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

MODEL = "claude-opus-5"
FALLBACK_MODEL = "claude-opus-4-8"


class P11Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    anthropic_api_key: str | None = None
    ai_model: str = MODEL


class CompetitorView(BaseModel):
    name: str
    positioning: str
    strengths: list[str]
    weaknesses: list[str]
    evidence: list[str]


class Opportunity(BaseModel):
    title: str
    why: str
    action: str
    channel: Literal["ads", "website", "both"]
    evidence: list[str]


class Angle(BaseModel):
    headline_idea: str
    rationale: str


class Interpretation(BaseModel):
    summary: str
    competitors: list[CompetitorView]
    opportunities: list[Opportunity]
    messaging_angles: list[Angle]
    caveats: list[str]


class InterpretError(Exception):
    pass


_S = {"type": "string"}
_L = {"type": "array", "items": _S}


def _obj(props: dict) -> dict:
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


SCHEMA = _obj({
    "summary": _S,
    "competitors": {"type": "array", "items": _obj({"name": _S, "positioning": _S, "strengths": _L, "weaknesses": _L, "evidence": _L})},
    "opportunities": {"type": "array", "items": _obj({"title": _S, "why": _S, "action": _S,
                                                      "channel": {"type": "string", "enum": ["ads", "website", "both"]}, "evidence": _L})},
    "messaging_angles": {"type": "array", "items": _obj({"headline_idea": _S, "rationale": _S})},
    "caveats": _L,
})

SYSTEM = (
    "You are a PPC strategist for an Australian chauffeur business. You receive OBSERVATIONS only: text read from "
    "competitors' public websites, what the owner saw in Google results, coverage counts, and searches for competitor "
    "brands in the owner's OWN Google Ads account. Interpret them.\n"
    "Rules: every strength, weakness and opportunity must cite evidence keys exactly as given (obs:<id>, gap:<term>, "
    "demand:<name>). Never claim knowledge of a competitor's Google Ads budget, bids, keywords, conversion data or "
    "performance — nobody outside their account can see that; if something can't be known, say so in caveats. Say "
    "'their website says…' rather than stating their claims as fact. 3–6 opportunities, specific and doable (e.g. a "
    "dedicated page, an ad group, a message to test); messaging angles must not copy competitor wording or use their "
    "brand names, and must not invent claims (the owner verifies USPs). Australian English."
)


def evidence_block(obs: list[dict], gap_rows: list[dict], demand: dict[str, dict], names: dict[int, str]) -> tuple[str, set[str]]:
    keys, lines = set(), ["OBSERVATIONS"]
    for o in obs:
        k = f"obs:{o['id']}"
        keys.add(k)
        d = o["data"]
        who = names.get(o["competitor_id"], "?")
        if o["kind"] == "page":
            lines.append(f"[{k}] {who} page {o['source']} — title: {d.get('title', '')} | H1: {' / '.join(d.get('h1', []))} | "
                         f"H2: {' / '.join(d.get('h2', [])[:8])} | CTAs: {', '.join(d.get('ctas', [])[:5])} | prices: "
                         f"{', '.join(d.get('prices', [])[:5]) or 'none'} | trust: {', '.join(d.get('trust', [])) or 'none'}")
        elif o["kind"] == "serp":
            lines.append(f"[{k}] Owner saw {who} in Google for '{d.get('query', '')}' ({d.get('placement', '')}"
                         f"{', position ' + str(d['position']) if d.get('position') else ''}) on {o['observed_on']}: {d.get('text', '')}")
        else:
            lines.append(f"[{k}] Owner note about {who}: {d.get('text', '')}")
    lines.append("\nCONTENT GAPS (a competitor has a dedicated page, we don't)")
    for g in gap_rows:
        k = f"gap:{g['term']}"
        keys.add(k)
        lines.append(f"[{k}] {g['term']}: {', '.join(g['competitors'])} (our pages mentioning it: {g['our_mentions']})")
    lines.append("\nSEARCHES FOR COMPETITOR BRANDS IN OUR OWN ACCOUNT (last 12 months)")
    for name, d in demand.items():
        k = f"demand:{name}"
        keys.add(k)
        lines.append(f"[{k}] {name}: {d['terms']} search terms, {d['impressions']} impressions, {d['clicks']} clicks, AUD {d['cost']}, "
                     f"{d['conversions']} conversions; top: {', '.join(t['search_term'] for t in d['top'][:5])}")
    return "\n".join(lines), keys


def clean(i: Interpretation, keys: set[str]) -> Interpretation:
    dropped = 0
    for part in [*i.competitors, *i.opportunities]:
        ok = [e for e in part.evidence if e in keys]
        dropped += len(part.evidence) - len(ok)
        part.evidence = ok
    i.opportunities = [o for o in i.opportunities if o.evidence]
    if dropped:
        i.caveats.append(f"{dropped} evidence reference(s) did not match any observation and were removed.")
    return i


def with_claude(text: str, keys: set[str], settings: P11Settings) -> tuple[Interpretation, int | None, str]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        r = client.beta.messages.create(
            model=settings.ai_model, max_tokens=16000, thinking={"type": "adaptive"},
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-06-01"], fallbacks=[{"model": FALLBACK_MODEL}],
            system=SYSTEM, messages=[{"role": "user", "content": text}])
    except anthropic.AuthenticationError as e:
        raise InterpretError("Claude API key is invalid (ANTHROPIC_API_KEY)") from e
    except anthropic.RateLimitError as e:
        raise InterpretError("Claude API rate limit reached — try again in a minute") from e
    except anthropic.APIStatusError as e:
        raise InterpretError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise InterpretError("Could not reach the Claude API (network)") from e
    if r.stop_reason == "refusal":
        raise InterpretError("Claude declined this request")
    if r.stop_reason == "max_tokens":
        raise InterpretError("Claude's answer was cut off (max_tokens)")
    out = next((b.text for b in r.content if b.type == "text"), None)
    if not out:
        raise InterpretError("Claude returned no text")
    try:
        parsed = Interpretation.model_validate_json(out)
    except ValueError as e:
        raise InterpretError(f"Claude's answer did not match the format: {str(e)[:200]}") from e
    return clean(parsed, keys), r.usage.output_tokens, r.model


def template(gap_rows: list[dict], demand: dict[str, dict], messaging: dict[str, dict]) -> Interpretation:
    opps = [Opportunity(title=f"Add a dedicated '{g['term']}' page", channel="both", evidence=[f"gap:{g['term']}"],
                        why=f"{', '.join(g['competitors'])} have a page for it; you have none (mentioned on {g['our_mentions']} of your pages).",
                        action=f"Create a landing page for '{g['term']}' and point a matching ad group to it.")
            for g in gap_rows[:5]]
    for name, d in demand.items():
        if d["clicks"]:
            opps.append(Opportunity(title=f"Decide on '{name}' brand searches", channel="ads", evidence=[f"demand:{name}"],
                                    why=f"You paid AUD {d['cost']} for {d['clicks']} clicks on searches for {name}, {d['conversions']} conversions.",
                                    action="Either add them as negatives (see Search Terms) or run a small, clearly separate competitor campaign."))
    views = [CompetitorView(name=n, positioning=(m.get("home_h1") or [m.get("home_title", "")])[0] if (m.get("home_h1") or m.get("home_title")) else "",
                            strengths=[f"Website mentions: {', '.join(m['trust'])}"] if m.get("trust") else [],
                            weaknesses=[] if m.get("prices") else ["No prices shown on the pages read"], evidence=[])
             for n, m in messaging.items()]
    return Interpretation(summary="Rule-based summary (AI is off): content gaps and competitor-brand searches from the observations.",
                          competitors=views, opportunities=opps, messaging_angles=[],
                          caveats=["Based only on the pages that could be read and your own account's data.",
                                   "Competitors' Google Ads data (budgets, keywords, results) is not visible to anyone outside their account."])
