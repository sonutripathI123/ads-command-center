# P01 Changelog

## 2026-09-23 — initial build
- Next.js 16 + TypeScript + Tailwind 4 scaffold.
- Shell layout, 21-section navigation, website/account selector (mock data), status pills, alert strip.
- Overview, Settings (read-only flags), placeholder route for unbuilt sections.
- Contract/boundary tests in `backend/app/modules/p01_shell/tests`.
- Status: `review`.

## 2026-09-23 — approved cross-module change (requested by P02)
- `AppShell` gains two optional props: `headerRight` (slot, used for the P02 user menu) and `bareRoutes`
  (routes rendered without sidebar/top bar, used for P02 `/login`). Wired in `app/layout.tsx`.
- Shell still imports no feature module; nav.json unchanged (Account is reached from the user menu).
- Approved by user 2026-09-23.

## 2026-09-28 — approved cross-module change (requested by P03, "Request 2")
- Scope selector shows real websites (P03) and connected ads accounts via a `scopeLoader` prop; reloads on navigation;
  remembered selections that no longer exist fall back to "all".
- Removed `src/shell/mock/scope.ts` and the "Demo data" banner. Types moved to `src/shell/scope-types.ts`.
- New `src/app/ShellFrame.tsx` (client) composes the shell with P02/P03 pieces; `layout.tsx` renders it.
- Overview tile notes updated. Shell still imports no feature module and calls only the P00 API.

## 2026-10-05 — global "Sync now" (additive composition change, requested by the owner)
- `frontend/src/app/ShellFrame.tsx` now also composes `<SyncAllButton />` (new frontend module `src/modules/data-sync`) into
  the header, next to the user menu — same pattern as `UserMenu`. One click runs the existing read-only syncs (Google Ads
  per account, GA4 + Search Console per website), then a monitoring check, then reloads the page. It only calls existing
  endpoints (P05/P06/P18, analyst permission); no shell file under `src/shell/` changed and no Google Ads change is made.

