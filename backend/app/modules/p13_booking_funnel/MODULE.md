# P13 — Booking Funnel & Revenue Attribution

**Status:** approved_frozen (user approved 2026-10-06)

## Purpose
Show, per website, how ad impressions become clicks, paid visits, leads, bookings and revenue — with the rate and cost
at each step, the change vs the previous period, and where the funnel leaks. Each stage names its data source; stages
that aren't measured show "not measured" (never zero); estimates are labelled.

## Stages (`funnel.py`)
| Stage | Source |
|---|---|
| Ad impressions, clicks | P05 (linked Google Ads account) |
| Paid visits | P06 GA4 — Paid Search (+ Cross-network) sessions |
| Leads (estimate) | P06 GA4 events with role *lead* (mapped, else recognised by name) × paid share of sessions |
| Bookings / revenue from Google Ads | P06 bookings with gclid or utm google/cpc |
Rates are taken from the previous measured stage. If GA4 starts part-way through the period, click → visit isn't
compared (and the report says so).

## Bottlenecks
No linked account · no GA4 · no lead event · no bookings imported · no bookings attributed to Google Ads · low CTR ·
clicks lost before GA4 · low visit → lead · low lead → booking · revenue below spend · unconfirmed event roles.
Benchmarks are rough and used only to flag.

## Also shown
Google-Ads-reported campaign figures (cost, conversions, value, CPA, reported ROAS) and booking quality by channel
(count, revenue, average value).

## Known limit — change request CR-P13-1 (needs your approval)
Revenue by **campaign/keyword** needs per-booking rows (gclid/utm_campaign, amount, status) from P06, whose interface
only exposes totals. Proposed additive, read-only P06 interface function `booking_rows(db, d1, d2, website_id)`. P06 is
frozen, so this waits for approval. (Also: 0 bookings are imported today — the Driver App link request is pending.)

## Files
| File | Role |
|---|---|
| `backend/app/modules/p13_booking_funnel/interface.py` | **public interface**: `website_funnel` (for P18/P19) |
| `…/funnel.py` (pure), `service.py`, `router.py` | `/api/v1/funnel` (read-only, no tables) |
| `frontend/src/modules/funnel/*`, `frontend/src/app/bookings-revenue/page.tsx` | Bookings / Revenue page |

## Acceptance criteria
- [x] Click → lead → booking → revenue model; available attribution links; booking quality by channel;
  revenue-aware campaign view (Google-Ads-reported); bottleneck detection.
- [ ] Campaign-level booking revenue (CR-P13-1). [x] User review and approval (2026-10-06).
