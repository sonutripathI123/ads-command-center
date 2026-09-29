# P11 — Competitor Intelligence

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Compare the business with named competitors using **public** information only, and keep facts (observations) apart
from interpretation. Never claims competitors' Google Ads data (budgets, bids, keywords, results) — nobody outside
their account can see it.

## Observations (facts, each with its source)
| Kind | Where it comes from | Needs |
|---|---|---|
| page | Competitor's public website: robots.txt honoured, sitemap-led (homepage + service/location pages first, max 12, 1.5 s delay). Title, H1/H2, CTAs, prices, trust signals. | flag `competitor.research.enabled` |
| serp | What the owner saw in Google (search, ad/organic/maps, position, text) — entered by hand. Google result pages are **never scraped** (against Google's terms). | — |
| note | Anything else the owner knows (radio ads, pricing heard from customers …). | — |
| search demand | Computed live from the account's **own** P05 search terms that mention the competitor's brand (last 12 months). | — |
Re-running research keeps older page rows as history (`current = false`); only the latest run is compared.

## Comparison (pure, `analysis.py`)
- Service and location coverage: our pages (P03, linked websites) vs each competitor — pages mentioning a term and pages
  dedicated to it (URL/title/H1). **Gap** = a competitor has a dedicated page and we don't; **advantage** = the reverse.
- Landing-page themes (airport, corporate, wedding, formal, cruise, limo, tours, events, hourly); messaging (homepage
  headline, CTAs, prices, trust signals).

## Interpretation (separate, labelled)
Claude (flag `ai.live_calls.enabled` + key) or a rule-based template: positioning, strengths/weaknesses, opportunities
(ads / website / both), messaging angles, caveats. Every point cites evidence keys (`obs:<id>`, `gap:<term>`,
`demand:<name>`); references that don't exist are removed and counted in caveats. Stored in `competitor_analyses`.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p11_competitor_intel/interface.py` | **public interface**: `competitor_summary` (for P14/P15/P19) |
| `…/research.py`, `analysis.py`, `interpret.py` | public-site research, comparison, interpretation |
| `…/service.py`, `router.py`, `models.py` | `/api/v1/competitors` |
| `backend/alembic/versions/0016_p11_competitor_intel.py` | migration |
| `frontend/src/modules/competitors/*`, `frontend/src/app/competitors/page.tsx` | Competitors page |

## Acceptance criteria
- [x] Public website research; public SERP observations (manual); service/location coverage; messaging; landing-page
  themes; content gaps; observations separate from AI interpretation; no private Ads data claimed.
- [ ] Flag `competitor.research.enabled` switched on by the owner; real competitors added and researched.
- [ ] User review and approval.
