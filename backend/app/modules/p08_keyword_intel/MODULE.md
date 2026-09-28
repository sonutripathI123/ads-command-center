# P08 — Keyword & Search-Term Intelligence

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Turn P05 search-term/keyword data + P21 rules into: an intent class per search term, **negative keyword
suggestions with evidence and confidence** for human review, and keyword insights. Nothing is sent to Google Ads;
accepted negatives are exported (copy for the Google Ads UI, or CSV for Google Ads Editor).

## How suggestions are made (`analysis.py`, deterministic)
| Source | Match | Level | Confidence |
|---|---|---|---|
| search contains an **excluded term** (P21) | Phrase on the term | all campaigns | 95% · 60% if a multi-word term also appears with your service words · 50% if it converted |
| search names a **place you don't serve** (and none you do) | Phrase | all campaigns | 85% |
| **costly, non-converting, not clearly relevant** search (≥ min spend & clicks) | Exact | its campaign | 50–60% |
| a word common to **≥ 3 non-converting searches**, ≥ 2× min spend, not a service/area/brand word | Phrase | all campaigns | 40% |

Relevant searches (service + area, or brand) are never suggested as negatives. Review decisions survive re-analysis;
suggestions not found in a later run become "stale".

Intents: service_location, service, location_only, excluded, wrong_location, competitor, brand, unclassified.

Insights: wasters, winners (cheapest cost/conv first; flags above target CPA), low Quality Score, duplicates
(within a campaign, enabled campaigns only), idle (enabled campaigns only), expansion candidates.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p08_keyword_intel/interface.py` | **public interface**: `accepted_negatives`, `classify_terms` |
| `…/analysis.py` | pure classification / candidate / insight logic |
| `…/service.py`, `router.py`, `models.py` | persistence, `/api/v1/keywords`, tables |
| `backend/alembic/versions/0006_p08_keyword_intel.py` | migration |
| `frontend/src/modules/keyword-intel/*` | NegativesPage (status tabs, **confidence filter**, bulk review, export), InsightsPage |
| `frontend/src/app/search-terms/negatives/page.tsx`, `frontend/src/app/keywords/insights/page.tsx` | routes (linked from the P05 pages) |

## Routes (`/api/v1/keywords/accounts/{id}`)
`POST /analyze?days=` (recommend) · `GET /negatives?status=&min_confidence=` (read) · `POST /negatives/review` (approve) ·
`GET /negatives/export?fmt=csv|text` (read) · `GET /classifications?intent=` (read) · `GET /insights?days=` (read)

## Not yet
- AI (Claude) classification of "unrecognised" searches — comes with P14 (`ai.live_calls.enabled`).
- Pushing negatives to Google Ads — P16 approval + P17 execution.

## Acceptance criteria
- [x] Intent classification, business-value classification, negative candidates with evidence + confidence.
- [x] Duplicate/overlap detection, keyword expansion ideas, waste/winner/QS insights.
- [x] Human review (accept/reject), export; no live mutation.
- [x] Real run on Corporate Cars Melbourne (2026-09-28).
- [ ] User review and approval.
