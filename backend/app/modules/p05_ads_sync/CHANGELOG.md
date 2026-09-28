# P05 Changelog

## 2026-09-28 — initial build
- Warehouse tables (migration `0004_p05`), sync engine (5 independent GAQL steps, daily metrics replace-window).
- Sync runs with status/errors, background execution, CLI, stale-run expiry.
- Aggregation API + backend interface for analysis modules.
- Frontend: Campaigns (tiles, daily spend chart, table, all-paused warning), Ad Groups, Keywords, Search Terms.
- Registry: `depends_on` now P02 + P04 (P02 needed for route permissions).
- First real sync: Corporate Cars Melbourne, 2026-07-01..2026-09-28, success.
- Status: `review`.
