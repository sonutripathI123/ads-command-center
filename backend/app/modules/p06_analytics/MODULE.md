# P06 — Analytics & Conversion Data

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Bring website analytics and real bookings next to the Ads data, keeping three kinds of numbers apart:
**observed** (GA4, Search Console), **attributed** (Google Ads conversions — read from P05) and **confirmed**
(bookings). Detect tracking problems automatically.

## Data
- GA4 Data API (service account, read-only): daily sessions / engaged / users / key events by channel; daily events.
- Search Console (service account, read-only): daily clicks / impressions / position by query.
- Conversion mapping: each GA4 event → lead | booking | micro | ignore (suggested automatically, set by approver).
- Bookings: CSV import now (id, date, amount + optional service date, status, service, website, channel, gclid,
  UTMs). **Names, emails and phone numbers are ignored and never stored.** Cancelled bookings are excluded.
  Driver App adapter: separate, needs a read-only endpoint in the Driver App (its own approval).

## Tracking health checks
no GA4 linked · no GA4 data · GA4 started late · no key events · form_start without submit/lead event ·
no event mapped as lead/booking · GA4 paid sessions < 60 % of Ads clicks · Ads conversions but no GA4 key events ·
Search Console not linked · no bookings imported.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p06_analytics/interface.py` | **public interface**: `website_overview`, `bookings_summary`, `tracking_health` |
| `…/adapters/google.py` | service-account JWT auth (via `cryptography`), GA4 runReport, Search Console query — read-only |
| `…/service.py`, `router.py`, `models.py` | sync, overview + health, mappings, bookings import; `/api/v1/conversions` |
| `backend/alembic/versions/0008_p06_analytics.py` | migration |
| `frontend/src/modules/conversions/*`, `frontend/src/app/conversions/page.tsx` | Conversions & Analytics page |

## Configuration
`GOOGLE_SERVICE_ACCOUNT_FILE` in backend/.env. The service account needs **Viewer** on each GA4 property and
**Full/Restricted user** on each Search Console property.

## Acceptance criteria
- [x] GA4 integration; conversion event mapping; calls/forms/quotes/bookings where available (events + CSV).
- [x] Booking adapter interface (CSV) + confirmed vs observed vs attributed separation.
- [x] Real sync of Corporate Cars Melbourne (2026-09-28): 380 sessions, 9k Search Console rows; health found 2 critical issues.
- [ ] Driver App live adapter (needs approval to change the Driver App).
- [ ] Offline conversion upload to Google Ads (later: P13 + P17).
- [ ] User review and approval.
