# P10 — Landing Page & CRO Intelligence

**Status:** approved_frozen (user approved 2026-10-06)

## Purpose
Check every page the account's ads send people to — on any domain the business owns (e.g. corporatecarsmelbourne.com.au
and opalchauffeurs.com.au) — for the things that decide whether a click becomes a booking, and turn the findings into a
website implementation brief for the developer. Nothing is changed on the websites or in Google Ads.

## How a check works
1. Landing URLs come from P05 ads (last 90 days, removed ads skipped; `www.`/trailing slash merged), biggest spend first,
   max 25. Each URL carries its ads, ad groups, keywords (by clicks) and spend.
2. `fetch.py` fetches each URL once (robots.txt honoured, 1 s delay, 20 s timeout, server response time measured).
   Gated by the P03 flag `crawler.enabled` (read-only here; already approved for the business's own sites).
3. `extract.py` reads CRO signals: title/H1/H2, CTAs and whether one is near the top, tel: links, booking links, forms
   (fields, required, button text), trust signals (reviews, experience, accreditation, guarantees, awards, clients),
   prices, schema, GA4/GTM and Google Ads tags, scripts, images/alt, page weight, mobile viewport.
4. `rules.py` → findings by category (tracking · intent · cta · form · trust · mobile · speed · technical) with
   evidence and a recommendation; score 0–100 (critical −20, warning −8, info −2; page not loading = 0).
   - Intent: click-weighted keyword coverage on the page, H1 vs top keywords, ad headlines vs page headline, service area.
   - Tracking: P06 critical tracking issues are attached to pages on linked websites that have a form/booking link;
     domains not added under Websites get "tracking not verified".
5. Implementation brief (`brief.py`): Claude (flag `ai.live_calls.enabled` + key) or a template — prioritised changes
   (owner, effort), copy suggestions (H1, CTAs, trust line with [placeholders], never invented facts), form and tracking
   changes, acceptance checks. Download as Markdown.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p10_landing_cro/interface.py` | **public interface**: `landing_scores` (for P14/P19) |
| `…/fetch.py`, `extract.py`, `rules.py`, `brief.py` | fetch, signals, checks, brief writer (pure except fetch/Claude) |
| `…/service.py`, `router.py`, `models.py` | runs, history, briefs; `/api/v1/landing-pages` |
| `backend/alembic/versions/0015_p10_landing_cro.py` | migration |
| `frontend/src/modules/landing-pages/*`, `frontend/src/app/landing-pages/page.tsx` | Landing Pages page |

## Limits (stated in the UI)
- No JavaScript rendering: content injected by JS widgets may be missed. Speed = our server's measured response time,
  not a full PageSpeed/Core Web Vitals test.

## Acceptance criteria
- [x] Keyword/ad/page intent matching; CTA; booking form; trust; mobile; speed/technical; implementation briefs.
- [x] Real check of the 3 Corporate Cars / Opal landing pages.
- [x] User review and approval (2026-10-06).
