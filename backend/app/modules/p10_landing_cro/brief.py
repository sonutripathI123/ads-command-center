"""P10 — website implementation brief for one landing page. Live: Claude via the official `anthropic` SDK with a strict
JSON schema (same safety pattern as P09/P14). Template: built deterministically from the findings."""
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

MODEL = "claude-opus-5"
FALLBACK_MODEL = "claude-opus-4-8"
SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}
OWNER = {"tracking": "developer", "technical": "developer", "speed": "developer", "mobile": "developer", "form": "developer",
         "intent": "content", "cta": "content", "trust": "owner"}


class P10Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    anthropic_api_key: str | None = None
    ai_model: str = MODEL


class Change(BaseModel):
    title: str
    why: str
    how: str
    owner: Literal["developer", "content", "owner"]
    effort: Literal["small", "medium", "large"]


class Copy(BaseModel):
    h1: str
    subheadline: str
    primary_cta: str
    secondary_cta: str
    trust_line: str


class Brief(BaseModel):
    summary: str
    priority_changes: list[Change]
    copy_suggestions: Copy
    form_changes: list[str]
    tracking_changes: list[str]
    acceptance_checks: list[str]
    notes: str


class BriefError(Exception):
    pass


_STR = {"type": "string"}
_LIST = {"type": "array", "items": _STR}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["summary", "priority_changes", "copy_suggestions", "form_changes", "tracking_changes", "acceptance_checks", "notes"],
    "properties": {
        "summary": _STR,
        "priority_changes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["title", "why", "how", "owner", "effort"],
            "properties": {"title": _STR, "why": _STR, "how": _STR,
                           "owner": {"type": "string", "enum": ["developer", "content", "owner"]},
                           "effort": {"type": "string", "enum": ["small", "medium", "large"]}}}},
        "copy_suggestions": {"type": "object", "additionalProperties": False,
                             "required": ["h1", "subheadline", "primary_cta", "secondary_cta", "trust_line"],
                             "properties": {k: _STR for k in ["h1", "subheadline", "primary_cta", "secondary_cta", "trust_line"]}},
        "form_changes": _LIST, "tracking_changes": _LIST, "acceptance_checks": _LIST, "notes": _STR,
    },
}

SYSTEM = (
    "You are a conversion-rate specialist writing a website implementation brief for an Australian chauffeur business's "
    "Google Ads landing page. The reader is the web developer / site owner. Australian English, plain and specific.\n"
    "Use ONLY the evidence given (findings, page signals, keywords, ad headlines). Order priority_changes by impact: "
    "conversion tracking first (without it nothing can be measured), then broken/mobile issues, then message match with "
    "the searches, CTA and booking form, trust, speed. 4–8 changes; each 'how' must be concrete enough to implement.\n"
    "Never invent facts: no review counts, ratings, awards, years in business, prices or accreditations that are not in the "
    "evidence — write a placeholder like [your Google rating] for the owner to fill in. copy_suggestions must match the top "
    "keywords and ad headlines (H1 at most 70 characters, CTAs at most 25). acceptance_checks: how to verify each change "
    "(e.g. 'Submit a test quote → GA4 DebugView shows generate_lead'). Put anything the owner must confirm in notes."
)


def brief_input(url: str, score: int, findings: list[dict], signals: dict | None, ctx: dict, locations: list[str],
                services: list[str]) -> str:
    s = signals or {}
    lines = [f"Landing page: {url}", f"Score: {score}/100",
             f"Traffic (90 days): {ctx.get('clicks', 0)} clicks, AUD {ctx.get('cost', 0):.2f}, {ctx.get('conversions', 0)} conversions",
             f"Ad groups using it: {', '.join(ctx.get('ad_groups', [])[:10]) or '(none)'}",
             "Top keywords (clicks): " + ", ".join(f"{k['text']} ({k.get('clicks', 0)})" for k in ctx.get("keywords", [])[:20]),
             "Ad headlines: " + " | ".join(dict.fromkeys(h for a in ctx.get("ads", []) for h in a.get("headlines", [])))[:1500],
             f"Areas served: {', '.join(locations[:12])}", f"Services: {', '.join(services[:15])}",
             f"Page title: {s.get('title', '')}", f"H1: {' | '.join(s.get('h1', []))}", f"H2: {' | '.join(s.get('h2', [])[:12])}",
             f"CTAs: {', '.join(s.get('ctas', [])[:12])}",
             "Forms: " + "; ".join(f"{len(f['fields'])} fields ({', '.join(x['name'] for x in f['fields'][:12])}), button '{f.get('submit_text', '')}'"
                                   for f in s.get("forms", [])),
             f"Trust signals present: {', '.join(k for k, v in s.get('trust', {}).items() if v) or 'none'}",
             "", "Findings:"]
    for f in sorted(findings, key=lambda f: SEV_ORDER[f["severity"]]):
        ev = "; ".join(f"{a}: {b}" for a, b in f.get("evidence", [])[:5])
        lines.append(f"- [{f['severity']}/{f['category']}] {f['title']} — {f['detail']} Recommendation: {f['recommendation']}"
                     + (f" Evidence: {ev}" if ev else ""))
    return "\n".join(lines)


def write_with_claude(text: str, settings: P10Settings) -> tuple[Brief, int | None, str]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        r = client.beta.messages.create(
            model=settings.ai_model, max_tokens=16000, thinking={"type": "adaptive"},
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-06-01"], fallbacks=[{"model": FALLBACK_MODEL}],
            system=SYSTEM, messages=[{"role": "user", "content": text}])
    except anthropic.AuthenticationError as e:
        raise BriefError("Claude API key is invalid (ANTHROPIC_API_KEY)") from e
    except anthropic.RateLimitError as e:
        raise BriefError("Claude API rate limit reached — try again in a minute") from e
    except anthropic.APIStatusError as e:
        raise BriefError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise BriefError("Could not reach the Claude API (network)") from e
    if r.stop_reason == "refusal":
        raise BriefError("Claude declined this request")
    if r.stop_reason == "max_tokens":
        raise BriefError("Claude's answer was cut off (max_tokens)")
    text_out = next((b.text for b in r.content if b.type == "text"), None)
    if not text_out:
        raise BriefError("Claude returned no text")
    try:
        brief = Brief.model_validate_json(text_out)
    except ValueError as e:
        raise BriefError(f"Claude's answer did not match the brief format: {str(e)[:200]}") from e
    return brief, r.usage.output_tokens, r.model


def template_brief(url: str, findings: list[dict], ctx: dict, locations: list[str]) -> Brief:
    ordered = sorted(findings, key=lambda f: (SEV_ORDER[f["severity"]], 0 if f["category"] == "tracking" else 1))
    changes = [Change(title=f["title"], why=f["detail"] or f["title"], how=f["recommendation"], owner=OWNER.get(f["category"], "developer"),
                      effort="small" if f["severity"] == "info" else "medium") for f in ordered if f["severity"] != "info"][:8]
    kw = next((k["text"] for k in ctx.get("keywords", [])), "Chauffeur Service")
    area = locations[0].title() if locations else "Melbourne"
    h1 = kw.title() if area.lower() in kw.lower() else f"{kw.title()} {area}"
    track = [f["recommendation"] for f in ordered if f["category"] == "tracking"]
    return Brief(
        summary=f"{len(findings)} issues found on {url}; {sum(f['severity'] == 'critical' for f in findings)} critical. Fix tracking first, then the page.",
        priority_changes=changes,
        copy_suggestions=Copy(h1=h1[:70], subheadline=f"Professional chauffeurs across {area}. Fixed quotes, easy online booking.",
                              primary_cta="Get an instant quote", secondary_cta="Call us now",
                              trust_line="[your Google rating] from [number] reviews · Licensed & insured"),
        form_changes=[f["recommendation"] for f in ordered if f["category"] == "form"] or ["Keep the quote form short (under 8 fields)."],
        tracking_changes=track or ["Confirm the booking form fires a GA4 key event that is imported into Google Ads."],
        acceptance_checks=["Page loads on a phone with the CTA visible without scrolling",
                           "Submit a test quote → GA4 DebugView shows the lead event, then it appears as a key event",
                           "The H1 contains the main searched service and area"],
        notes="Template brief (AI is off). Placeholders in [brackets] must be filled in by the owner.")


def to_markdown(url: str, b: Brief) -> str:
    out = [f"# Landing page brief — {url}", "", b.summary, "", "## Priority changes"]
    for i, c in enumerate(b.priority_changes, 1):
        out += [f"{i}. **{c.title}** _(owner: {c.owner}, effort: {c.effort})_", f"   - Why: {c.why}", f"   - How: {c.how}"]
    cs = b.copy_suggestions
    out += ["", "## Copy suggestions", f"- H1: {cs.h1}", f"- Sub-headline: {cs.subheadline}", f"- Primary CTA: {cs.primary_cta}",
            f"- Secondary CTA: {cs.secondary_cta}", f"- Trust line: {cs.trust_line}"]
    for title, items in (("Booking form", b.form_changes), ("Tracking", b.tracking_changes), ("How to check it's done", b.acceptance_checks)):
        out += ["", f"## {title}", *[f"- {x}" for x in items]]
    if b.notes:
        out += ["", "## Notes", b.notes]
    return "\n".join(out) + "\n"
