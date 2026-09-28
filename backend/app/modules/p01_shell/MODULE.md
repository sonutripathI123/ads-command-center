# P01 — Dashboard Shell

**Status:** approved_frozen (user approved 2026-09-23)

## Purpose
Global layout, navigation for all MID §19 sections, website/ads-account selector, global status/alerts.
Websites and ads accounts come from P03 through a loader passed in by `app/ShellFrame.tsx`. Contains **no** business logic for other modules.

## Files (all under `frontend/`)
| File | Role |
|---|---|
| `src/shell/index.ts` | **public interface** for module pages: `useScope`, `SCOPE_ALL`, `PageHeader`, `useModuleStatus`, `API_BASE`, types |
| `src/shell/nav.json` / `nav.ts` | section list: label, slug, owning moduleId |
| `src/shell/AppShell.tsx` | layout: sidebar, top bar, alert strip; props `headerRight` (slot) and `bareRoutes` (no chrome) |
| `src/shell/Sidebar.tsx` | navigation (shows owning module ID for unbuilt sections) |
| `src/shell/ScopeSelector.tsx`, `ScopeContext.tsx` | website / ads-account selector (persisted in localStorage) |
| `src/shell/StatusBar.tsx` | API health + kill-switch pills, alert strip |
| `src/shell/ModuleStatus.tsx` | registry statuses from P00 |
| `src/shell/ModulePlaceholder.tsx`, `PageHeader.tsx` | placeholder for unbuilt sections |
| `src/shell/api.ts` | read-only client for `/api/v1/foundation/*` |
| `src/shell/scope-types.ts` | scope data contract (`Website`, `AdsAccount`, `ScopeLoader`) |
| `src/app/ShellFrame.tsx` | client composition: AppShell + P02 UserMenu/public routes + P03 scope loader |
| `src/app/layout.tsx`, `globals.css` | root layout + design tokens |
| `src/app/page.tsx` | Overview |
| `src/app/[section]/page.tsx` | fallback page for every unbuilt section |
| `src/app/settings/page.tsx` | read-only environment + feature flags |

## How a module adds its page (no shell change)
Create `frontend/src/modules/<slug>/index.ts` + components, and `frontend/src/app/<slug>/page.tsx` that renders
them. Next.js picks the static route over `[section]`. Import shell features only from `@/shell`.

## Dependencies
P00 foundation API (health, modules, flags). `app/layout.tsx` injects P02's `UserMenu` into `headerRight` and passes
P02's public routes as `bareRoutes`.

## Acceptance criteria
- [x] All 21 MID §19 sections in navigation, each mapped to a registered owning module.
- [x] Website/account selector available to every page via `useScope()`.
- [x] Global status: backend health, kill-switch state, offline warning, notices.
- [x] Real websites/accounts in the selector (mock data removed 2026-09-28); no invented performance numbers.
- [x] Shell imports no feature module and calls no module API except P00.
- [x] Responsive (mobile drawer), light/dark.
- [x] User review and approval (2026-09-23).
