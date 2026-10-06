# P18 — Monitoring & Alerts

**Status:** approved_frozen (user approved 2026-10-06)

## Purpose
Watch each Google Ads account for things that need attention and keep one alert per problem until it clears.

## Checks (`checks.py`, last 7 full days vs the weekly average of the 28 days before)
| Code | Fires when |
|---|---|
| spend_spike | spend ≥ 1.5× usual (≥ AUD 50); critical at 2.5× |
| spend_stopped | usual spend ≥ AUD 50/week but none this week |
| conversion_drop | usual ≥ 3/week and this week ≤ half (critical at 0) |
| cpc_change | avg CPC ±30% (≥ 30 clicks both sides) |
| ctr_drop | CTR down ≥ 30% (≥ 1000 impressions) |
| no_recent_data | no impressions in the last 3 days (paused or not synced) — info |
| search_term_shift | new search terms (first seen this week) take ≥ 30% of spend (≥ AUD 20) |
| tracking:&lt;code&gt; | every critical P06 tracking-health issue of the linked websites |
Change-impact monitoring starts once P17 executes approved changes (none are executed yet).

## Alerts
One open alert per account + code: re-runs update it (occurrences, last seen); it **auto-resolves** when the condition
clears. Acknowledge (keeps it listed) or resolve by hand. Every run is recorded in `monitor_checks` (failures too).

## Scheduling
"Run checks now" on the page. For automatic runs, Windows Task Scheduler (e.g. daily 7am, after the Google Ads sync):
`cd backend && .venv\Scripts\python.exe -m app.modules.p18_monitoring.run` — does nothing unless flag
`monitoring.scheduled.enabled` is on.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p18_monitoring/interface.py` | **public interface**: `open_alerts` (for P19) |
| `…/checks.py` (pure), `service.py`, `router.py`, `models.py`, `run.py` | `/api/v1/monitoring`, scheduled entry point |
| `backend/alembic/versions/0017_p18_monitoring.py` | migration |
| `frontend/src/modules/monitoring/*`, `frontend/src/app/monitoring/page.tsx` | Monitoring & Alerts page |

## Acceptance criteria
- [x] Scheduled checks (flag-gated entry point); spend spikes; conversion drops; CPC changes; tracking failures;
  search-term shifts. [ ] Change-impact monitoring (after P17). [x] User review and approval (2026-10-06).
