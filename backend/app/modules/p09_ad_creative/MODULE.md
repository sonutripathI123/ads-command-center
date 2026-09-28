# P09 — Ad & Creative Intelligence

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Analyse existing responsive search ads (RSAs), write new RSA copy (Claude or template), check every line against
Google's RSA rules and claim/policy risks, and manage drafts → approved → CSV export. **Draft first; nothing is launched.**

## Checks (`checks.py`)
Errors (Google would reject / rule broken): headline > 30, description > 90, path > 15 or bad characters, '!' in a
headline, repeated punctuation, phone number in text, emoji, ALL-CAPS words (4+ letters), competitor names (P21),
too few/many headlines (3–15) or descriptions (2–4), duplicate headlines.
Warnings: unverified claims (#1, best, cheapest, guarantee, rating/award, free / % off, prices) unless listed as an approved
USP; fewer than 8 headlines / 4 descriptions; no main keyword in headlines; no call to action; no area mentioned.
Strength 0–100 is our estimate (Google's Ad Strength isn't available via read-only access).

## Writer (`writer.py`)
Live when flag `ai.live_calls.enabled` (declared by P14, read-only here) and ANTHROPIC_API_KEY are set: official
`anthropic` SDK, `claude-opus-5`, adaptive thinking, strict JSON schema, refusal fallback to `claude-opus-4-8`, stop
reasons handled, Pydantic validation; the model only sees ad group, keywords, landing page, P21 services/areas/brand,
approved USPs and existing headlines. Otherwise a deterministic template that passes all hard rules.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p09_ad_creative/interface.py` | **public interface**: `check_rsa`, `approved_drafts` |
| `…/checks.py`, `writer.py` | rules + writer |
| `…/service.py`, `router.py`, `models.py` | analysis, drafts, review, export; `/api/v1/creatives` |
| `backend/alembic/versions/0011_p09_ad_creative.py` | migration |
| `frontend/src/modules/creatives/*`, `frontend/src/app/ads-assets/page.tsx` | Ads & Assets page |

## Routes (`/api/v1/creatives`)
`GET /accounts` · `GET /accounts/{id}/analysis` · `GET /accounts/{id}/ad-groups` · `POST /accounts/{id}/drafts` (recommend) ·
`GET /accounts/{id}/drafts` · `PATCH /drafts/{id}` (recommend; approving needs approve, blocked while errors remain) ·
`GET /accounts/{id}/drafts/export` (Google Ads Editor CSV, status Paused).

## Acceptance criteria
- [x] Existing ad analysis; RSA generation; messaging variants (per ad group / USPs); claim validation; policy checks.
- [x] Draft first — no automatic launch; approval blocked by errors; CSV export as paused ads.
- [x] Real live draft for Corporate Cars (2026-09-28): 15/4, 0 findings.
- [ ] Performance comparison between ad variants (needs P20 experiments / more ad-level data).
- [ ] User review and approval.
