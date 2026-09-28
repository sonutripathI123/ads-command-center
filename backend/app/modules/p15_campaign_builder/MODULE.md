# P15 — AI Campaign Builder

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Turn existing keywords (usually one oversized ad group) into a **draft, paused** Search campaign organised by service
theme, with a landing page, keywords, ads (written through P09) and negatives per ad group, default settings, a launch
checklist and a Google Ads Editor export. Nothing is created in Google Ads by this module.

## How a draft is built (`builder.py`)
1. Keywords from the chosen P05 ad groups (last 90 days) → de-duplicated, sorted by conversions/clicks.
2. Negatives: self-drive rental brands (europcar, hertz, avis …) and keywords P08 classifies as unwanted — except
   "rental + driver" searches (e.g. "chauffeur driven car rental"), which are kept. Plus P21 excluded terms / places not
   served and P08 accepted negatives.
3. Themes (first match wins, plural-aware): Airport · Weddings & Formals · Cruise · Limousine · Tours & Hourly · Events ·
   Corporate & Executive · Chauffeur (general). Up to 30 keywords per ad group (rest held back as "reserve").
   Match type: EXACT if the keyword converted, else PHRASE. No match → "unassigned" for the user to place.
4. Landing page from P03 scanned pages: URL must contain the theme's primary word; title/H1, CTA and form/phone add
   points; slow/thin pages and long niche URLs lose points. General chauffeur theme → homepage.
5. Settings: Search only, **Paused**, budget, location presence; Maximize Clicks + max CPC while P06 reports critical
   tracking issues, otherwise Maximize Conversions.
6. Checklist: tracking · landing pages · approved ads · keywords · negatives · budget · (manual) location option ·
   (manual) primary conversion. Approval needs everything except tracking to pass (the campaign stays paused).

## Files
| File | Role |
|---|---|
| `backend/app/modules/p15_campaign_builder/interface.py` | **public interface**: `get_campaign_draft`, `approved_campaign_drafts` |
| `…/builder.py` | pure clustering / landing / settings / checklist |
| `…/service.py`, `router.py`, `models.py` | build, edit ops, write ads (P09), approve, export; `/api/v1/campaign-builder` |
| `backend/alembic/versions/0012_p15_campaign_drafts.py` | migration |
| `frontend/src/modules/campaign-builder/*`, `frontend/src/app/campaign-builder/page.tsx` | Campaign Builder page |

## Acceptance criteria
- [x] Goal/service/location input; campaign structure; ad groups; keywords; negative candidates; RSA ads (via P09);
  landing-page recommendation; launch checklist; draft/paused output (Editor CSV).
- [x] Real draft for Corporate Cars "Ad group 1" (284 keywords → 6 themed ad groups, 76 negatives).
- [ ] User review and approval.
