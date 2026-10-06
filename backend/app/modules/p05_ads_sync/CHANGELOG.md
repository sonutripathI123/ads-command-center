# P05 Changelog

## 2026-09-28 — initial build
- Warehouse tables (migration `0004_p05`), sync engine (5 independent GAQL steps, daily metrics replace-window).
- Sync runs with status/errors, background execution, CLI, stale-run expiry.
- Aggregation API + backend interface for analysis modules.
- Frontend: Campaigns (tiles, daily spend chart, table, all-paused warning), Ad Groups, Keywords, Search Terms.
- Registry: `depends_on` now P02 + P04 (P02 needed for route permissions).
- First real sync: Corporate Cars Melbourne, 2026-07-01..2026-09-28, success.
- Status: `review`.

## 2026-09-28 — for P08
- Interface: `list_accounts` (so analysis modules need not depend on P04).
- Keywords/Search Terms pages link to P08's insights and negative-suggestion pages.
- Status: `approved_frozen` (user approved 2026-09-28).

## 2026-10-06 — removed / paused campaigns shown truthfully (owner-approved change to a frozen module)
- Bug: campaigns deleted in Google Ads kept their last stored status (e.g. PAUSED) forever, and ad groups showed their own
  status ("Enabled") even when their campaign was paused or removed — so the dashboard looked as if ads were running.
- Fix: the sync now marks any campaign / ad group Google no longer returns as `REMOVED` (`_mark_missing`); ad groups carry
  `campaign_status` and an `effective_status` (own status AND campaign status: `Campaign paused`, `Removed`, ...) — new
  additive fields, existing ones unchanged. The Campaigns / Ad Groups routes hide removed rows that did nothing in the period
  (`?include_removed=true` shows them); rows that spent stay visible. The service/interface functions used by other modules
  keep returning everything. Pages show the effective status plus a "Show removed" toggle. Display + status bookkeeping
  only; nothing is sent to Google Ads. Tests: 3 added.
