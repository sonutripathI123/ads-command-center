"""P09 — RSA copy writer. Live: Claude via the official `anthropic` SDK with a strict JSON schema (same safety
pattern as P14: adaptive thinking, refusal fallback, stop-reason checks, Pydantic validation). Template: deterministic
copy built from keywords, area and USPs. Live needs flag `ai.live_calls.enabled` + ANTHROPIC_API_KEY."""
import re

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.modules.p09_ad_creative.checks import D_MAX, H_MAX, P_MAX

MODEL = "claude-opus-5"
FALLBACK_MODEL = "claude-opus-4-8"


class P09Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    anthropic_api_key: str | None = None
    ai_model: str = MODEL


class AdCopy(BaseModel):
    headlines: list[str]
    descriptions: list[str]
    path1: str
    path2: str
    notes: str


class WriterError(Exception):
    pass


SCHEMA = {"type": "object", "additionalProperties": False, "required": ["headlines", "descriptions", "path1", "path2", "notes"],
          "properties": {"headlines": {"type": "array", "items": {"type": "string"}},
                         "descriptions": {"type": "array", "items": {"type": "string"}},
                         "path1": {"type": "string"}, "path2": {"type": "string"}, "notes": {"type": "string"}}}

SYSTEM = (
    "You write Google Ads responsive search ads for an Australian chauffeur business. Australian English.\n"
    f"Hard rules: exactly 15 headlines of at most {H_MAX} characters each (count carefully, spaces included); exactly 4 "
    f"descriptions of at most {D_MAX} characters; path1 and path2 at most {P_MAX} characters, letters/numbers/hyphens only. "
    "No '!' in headlines, no phone numbers, no emojis, no words in ALL CAPS (short abbreviations such as CBD or VIP are fine), no competitor names. Only make claims that "
    "appear in the approved USPs (no '#1', 'best', 'cheapest', 'guaranteed', prices or discounts unless listed).\n"
    "Quality: at least 3 headlines contain the ad group's main keyword(s); at least 2 mention the area; include calls to "
    "action (book, get a quote); cover service, trust/quality, convenience and USPs; every headline must make sense on "
    "its own in any order; avoid near-duplicates. Descriptions: complete sentences with a clear next step. "
    "In notes, briefly say which USPs you used and anything the owner should verify."
)


def brief_text(ad_group: str, keywords: list[str], final_url: str, services: list[str], locations: list[str],
               usps: list[str], brand: str | None, existing: list[str]) -> str:
    return "\n".join([
        f"Ad group: {ad_group}", f"Main keywords: {', '.join(keywords[:15]) or '(none)'}",
        f"Landing page: {final_url or '(not set)'}", f"Brand: {brand or '(not provided)'}",
        f"Services offered: {', '.join(services[:20])}", f"Areas served: {', '.join(locations[:15])}",
        f"Approved USPs / claims (only these may be claimed): {'; '.join(usps) or '(none — make no claims)'}",
        f"Existing headlines (do not simply copy): {' | '.join(existing[:15]) or '(none)'}",
    ])


def write_with_claude(brief: str, settings: P09Settings) -> tuple[AdCopy, int | None, int | None, str]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        r = client.beta.messages.create(
            model=settings.ai_model, max_tokens=16000, thinking={"type": "adaptive"},
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-06-01"], fallbacks=[{"model": FALLBACK_MODEL}],
            system=SYSTEM, messages=[{"role": "user", "content": brief}])
    except anthropic.AuthenticationError as e:
        raise WriterError("Claude API key is invalid (ANTHROPIC_API_KEY)") from e
    except anthropic.RateLimitError as e:
        raise WriterError("Claude API rate limit reached — try again in a minute") from e
    except anthropic.APIStatusError as e:
        raise WriterError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise WriterError("Could not reach the Claude API (network)") from e
    if r.stop_reason == "refusal":
        raise WriterError("Claude declined this request")
    if r.stop_reason == "max_tokens":
        raise WriterError("Claude's answer was cut off (max_tokens)")
    text = next((b.text for b in r.content if b.type == "text"), None)
    if not text:
        raise WriterError("Claude returned no text")
    try:
        copy = AdCopy.model_validate_json(text)
    except ValueError as e:
        raise WriterError(f"Claude's answer did not match the ad format: {str(e)[:200]}") from e
    return copy, r.usage.input_tokens, r.usage.output_tokens, r.model


def _title(s: str) -> str:
    small = {"to", "and", "for", "in", "of", "a", "the", "with", "at", "on"}
    words = s.split()
    return " ".join(w if (w.lower() in small and i) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:P_MAX].strip("-")


def template_copy(ad_group: str, keywords: list[str], locations: list[str], usps: list[str], brand: str | None) -> AdCopy:
    area = _title(locations[0]) if locations else "Melbourne"
    kws = [_title(k) for k in keywords if len(k) <= H_MAX]
    service = kws[0] if kws else _title(ad_group)[:H_MAX]
    candidates = kws[:5] + [f"{service} {area}", f"Book Your {service}", f"{area} {service}", *(_title(u) for u in usps),
                            _title(brand) if brand else "", "Get an Instant Quote", "Book Online in Minutes",
                            "Professional Chauffeurs", "Luxury Late-Model Cars", "Airport & Corporate Transfers",
                            f"Chauffeur Service {area}", "Reliable, On-Time Pickups", "Meet & Greet Available",
                            "Request a Quote Today", "Travel in Comfort & Style", "Business & Event Travel",
                            "Easy Online Booking", "Friendly Local Drivers", "Clean, Comfortable Cars", "Punctual & Professional"]
    headlines, seen = [], set()
    for c in candidates:
        c = c.strip()
        if c and len(c) <= H_MAX and c.lower() not in seen:
            seen.add(c.lower())
            headlines.append(c)
        if len(headlines) == 15:
            break
    usp = "; ".join(usps[:2])
    descs = [f"{service} across {area}. Professional chauffeurs and clean, late-model cars. Book online.",
             f"Get a quick quote for your {service.lower()} and travel in comfort. Request yours today.",
             (f"{usp}. Easy online booking and friendly local drivers." if usp else "Easy online booking, friendly local drivers and punctual pickups."),
             f"Corporate, airport and event travel in {area}. Get your quote now."]
    descs = [d if len(d) <= D_MAX else d[: D_MAX - 1].rsplit(" ", 1)[0] + "." for d in descs]
    return AdCopy(headlines=headlines, descriptions=descs, path1=_slug(service) or "Chauffeur", path2=_slug(area),
                  notes="Template copy (AI is off). Review and personalise before use.")
