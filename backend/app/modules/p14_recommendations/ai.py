"""P14 — AI action plan. Live mode calls Claude (official `anthropic` SDK) with structured JSON output;
template mode builds the same shape deterministically. Live mode needs BOTH the flag `ai.live_calls.enabled`
and ANTHROPIC_API_KEY. The AI only sees evidence we already hold; it cannot change Google Ads.
"""
import json
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MODEL = "claude-opus-5"
FALLBACK_MODEL = "claude-opus-4-8"  # server-side fallback if the primary model declines


class P14Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    anthropic_api_key: str | None = None
    ai_model: str = MODEL


class Action(BaseModel):
    title: str
    why: str
    steps: list[str]
    owner: Literal["you", "website developer", "google ads"]
    effort: Literal["low", "medium", "high"]
    recommendation_ids: list[int]


class Week(BaseModel):
    week: int = Field(ge=1, le=4)
    focus: str
    tasks: list[str]


class ActionPlan(BaseModel):
    summary: str
    top_actions: list[Action]
    thirty_day_plan: list[Week]
    measure: list[str]
    caveats: list[str]


def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or list(props), "additionalProperties": False}


_STR, _STRS, _INTS = {"type": "string"}, {"type": "array", "items": {"type": "string"}}, {"type": "array", "items": {"type": "integer"}}
PLAN_SCHEMA = _obj({
    "summary": _STR,
    "top_actions": {"type": "array", "items": _obj({
        "title": _STR, "why": _STR, "steps": _STRS,
        "owner": {"type": "string", "enum": ["you", "website developer", "google ads"]},
        "effort": {"type": "string", "enum": ["low", "medium", "high"]}, "recommendation_ids": _INTS})},
    "thirty_day_plan": {"type": "array", "items": _obj({"week": {"type": "integer"}, "focus": _STR, "tasks": _STRS})},
    "measure": _STRS, "caveats": _STRS,
})

SYSTEM = (
    "You are a senior Google Ads specialist advising an Australian chauffeur business (airport transfers, corporate "
    "cars, weddings, events). You receive an account snapshot and a prioritised list of audit findings, each with "
    "measured evidence and an id. Write a practical action plan for the business owner in plain English.\n"
    "Rules: use only the facts provided; cite the finding ids each action addresses; order actions by business impact "
    "(fix measurement before optimising, stop waste before scaling); give concrete steps a non-expert can follow in "
    "Google Ads, GA4 or on the website; never promise or forecast a number of bookings or revenue; say plainly when "
    "data is missing or unreliable. At most 5 top actions, 4 weeks in the 30-day plan."
)


class AIError(Exception):
    pass


def build_prompt(snapshot: dict, recs: list[dict]) -> str:
    return "Account snapshot:\n" + json.dumps(snapshot, indent=1, default=str) + \
        "\n\nFindings (highest priority first):\n" + json.dumps(recs, indent=1, default=str)


def call_claude(prompt: str, settings: P14Settings) -> tuple[ActionPlan, int | None, int | None, str]:
    """→ (plan, input_tokens, output_tokens, model that answered)."""
    import anthropic

    from app.modules.p24_hardening.interface import with_retry

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = with_retry(
            lambda: client.beta.messages.create(
                model=settings.ai_model,
                max_tokens=16000,
                thinking={"type": "adaptive"},
                output_config={"effort": "high", "format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
                betas=["server-side-fallback-2026-06-01"],
                fallbacks=[{"model": FALLBACK_MODEL}],
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            ),
            retry_on=(anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError))
    except anthropic.AuthenticationError as e:
        raise AIError("Claude API key is invalid (ANTHROPIC_API_KEY)") from e
    except anthropic.RateLimitError as e:
        raise AIError("Claude API rate limit reached — try again in a minute") from e
    except anthropic.APIStatusError as e:
        raise AIError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise AIError("Could not reach the Claude API (network)") from e
    if response.stop_reason == "refusal":
        raise AIError("Claude declined this request")
    if response.stop_reason == "max_tokens":
        raise AIError("Claude's answer was cut off (max_tokens)")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise AIError("Claude returned no text")
    try:
        plan = ActionPlan.model_validate_json(text)
    except ValueError as e:
        raise AIError(f"Claude's answer did not match the plan format: {str(e)[:200]}") from e
    return plan, response.usage.input_tokens, response.usage.output_tokens, response.model


_OWNER = {"tracking": "website developer", "landing_pages": "website developer", "organic": "website developer"}


def template_plan(snapshot: dict, recs: list[dict]) -> ActionPlan:
    """Deterministic plan with the same shape, used when live AI is off."""
    top = recs[:5]
    actions = [Action(title=r["title"], why=r["reasoning"], steps=[r["proposed_action"]],
                      owner=_OWNER.get(r["category"], "google ads" if r["requires_approval"] else "you"),
                      effort="medium" if r["risk"] != "low" else "low", recommendation_ids=[r["id"]]) for r in top]
    crit = [r for r in recs if r["severity"] == "critical"]
    by_cat = lambda *cats: [r["title"] for r in recs if r["category"] in cats][:4]  # noqa: E731
    weeks = [
        Week(week=1, focus="Fix measurement", tasks=by_cat("tracking") or ["Confirm conversion tracking works end to end"]),
        Week(week=2, focus="Stop waste", tasks=by_cat("search_terms", "bidding") or ["Review search terms and bids"]),
        Week(week=3, focus="Structure, keywords and ads", tasks=by_cat("keywords", "ads") or ["Tidy ad groups and ads"]),
        Week(week=4, focus="Landing pages, then relaunch", tasks=by_cat("landing_pages", "account", "organic") or ["Review landing pages"]),
    ]
    return ActionPlan(
        summary=(f"{len(recs)} open findings, {len(crit)} critical. " if recs else "No open findings. ")
        + "This plan is generated from the audit rules (AI is switched off), ordered by priority.",
        top_actions=actions, thirty_day_plan=weeks,
        measure=["Enquiries recorded in GA4 (key events)", "Cost per enquiry in Google Ads",
                 "Confirmed bookings and revenue from Google Ads"],
        caveats=["Template plan — turn on live AI for a written, account-specific plan."] if recs else [])
