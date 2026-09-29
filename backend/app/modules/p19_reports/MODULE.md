# P19 — Reports & Exports

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Daily, weekly, monthly or custom reports for a Google Ads account or a website, stored as snapshots and exported as
CSV or a print-ready page (browser "Print → Save as PDF").

## Periods
Daily = yesterday · weekly = the 7 days to yesterday · monthly = last full calendar month · custom (≤ 2 years).
Compared with the previous period of the same kind.

## Content
- **Account:** headline, key figures vs previous period, campaigns, top search terms by cost, funnel of each linked
  website (P13), open recommendations (P14), approval decisions in the period (P16), open alerts (P18).
- **Website:** GA4 sessions/engagement/key events and channels, Search Console top queries, bookings by channel,
  tracking & data issues (P06), funnel (P13).
Everything comes from other modules' interfaces; the report adds no new facts. Snapshots (`report_runs`) don't change
when data changes later. Any signed-in user may generate a report (read-only).

## Files
| File | Role |
|---|---|
| `backend/app/modules/p19_reports/interface.py` | **public interface**: `generate_report` |
| `…/builder.py` (periods, KPIs), `render.py` (CSV, HTML), `service.py`, `router.py`, `models.py` | `/api/v1/reports` |
| `backend/alembic/versions/0018_p19_reports.py` | migration |
| `frontend/src/modules/reports/*`, `frontend/src/app/reports/page.tsx` | Reports page |

## Acceptance criteria
- [x] Daily/weekly/monthly; website-, account- and campaign-level; bookings/revenue; recommendations/actions; CSV/PDF.
- [ ] User review and approval.
