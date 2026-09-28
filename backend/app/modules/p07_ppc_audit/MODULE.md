# P07 — PPC Audit Engine

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
One-click, evidence-backed audit of a Google Ads account using everything the other modules know:
Ads data (P05), search-term classification (P08), business rules (P21), website + landing pages (P03),
GA4 / Search Console tracking health (P06). Produces a 0–100 health score and a prioritised issue list.
Read-only: it never changes Google Ads.

## Issue contract (MID §18 subset)
code · category · severity (critical/warning/info) · title · **observation** (measured facts only) · evidence[] ·
**reasoning** (interpretation) · proposed_action · expected_impact · confidence · risk (of making the change) ·
entity_type/entity_id · link. Dismissals are remembered by fingerprint (code + entity) across runs.

## Checks
account: all campaigns paused · campaign spend without conversions · very low conversion rate ·
tracking (from P06): no key events, form submit missing, Ads-vs-GA4 conversions, low paid sessions, no mapping, no GA4 ·
bidding: smart bidding on weak conversion data · above target CPA ·
search terms: spend on excluded/wrong-location searches · share of non-converting spend ·
keywords: broad match without conversions · low Quality Score · duplicates across active campaigns · oversized ad groups (> 100 = warning) ·
ads: enabled ad groups without an ad · RSAs with < 8 headlines / < 3 descriptions ·
landing pages: broken · other domain · weak (no CTA / form / phone, slow, thin) · no website linked ·
organic: brand search not on page 1.
Score = 100 − 15 × critical − 5 × warning − 1 × info (min 0).

## Files
| File | Role |
|---|---|
| `backend/app/modules/p07_ppc_audit/interface.py` | **public interface**: `latest_audit(db, account_id)` |
| `…/checks.py` | pure checks + score |
| `…/service.py`, `router.py`, `models.py` | gather via interfaces, persist, `/api/v1/audit` |
| `backend/alembic/versions/0009_p07_audit.py` | migration |
| `frontend/src/modules/audit/*`, `frontend/src/app/audit/page.tsx` | Account audit page (`/audit`) |

## Acceptance criteria
- [x] Account health, structure, ad groups, keywords, search terms, ads, conversion tracking, landing pages, budget/bid checks.
- [x] Evidence-backed issues in the recommendation shape; dismissals persist.
- [x] Real audit of Corporate Cars Melbourne (2026-09-28).
- [ ] Link from Overview (needs an approved P01 change).
- [ ] User review and approval.
