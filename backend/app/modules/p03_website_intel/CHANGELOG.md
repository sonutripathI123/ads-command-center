# P03 Changelog

## 2026-09-28 — initial build
- Websites CRUD + archive, linked Ads account (via P05 `list_accounts`), GA4/GSC fields.
- Polite crawler + stdlib extraction + issues; crawl runs; page signal history; ad landing-page mapping.
- Frontend: Websites list/add, website detail with Issues / All pages / Ad landing pages.
- Registry: depends_on P02, P05, P21 (was P21 only).
- Scanning is behind `crawler.enabled` (default off). There is no approved way yet to switch a flag on
  (P00 has read-only flags) — raised as a cross-module request.
- Status: `review`.
- `modules/websites/scope.ts` → `loadScope()` feeds the P01 scope selector (approved Request 2).
- Status: `approved_frozen` (user approved 2026-09-28).
