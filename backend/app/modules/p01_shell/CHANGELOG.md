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
