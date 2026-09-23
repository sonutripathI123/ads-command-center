# P01 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P01 |
| MODULE_NAME | Dashboard Shell |
| PURPOSE | Layout, navigation, scope selector, global status |
| OWNER_PATHS | `frontend/src/shell/`, `frontend/src/app/layout.tsx`, `frontend/src/app/globals.css`, `frontend/src/app/page.tsx`, `frontend/src/app/[section]/`, `frontend/src/app/settings/`, `frontend/package.json`, `frontend/*.config.*`, `frontend/tsconfig.json`, `frontend/README.md`, `backend/app/modules/p01_shell/` |
| OWNED_ROUTES | UI: `/`, `/settings`, `/[section]` fallback. API: none |
| OWNED_COMPONENTS | AppShell, Sidebar, ScopeSelector, StatusPills, AlertStrip, ModulePlaceholder, PageHeader |
| OWNED_SERVICES | none |
| OWNED_TABLES | none |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P00 `/api/v1/foundation/*` (read-only); P02 interface (future) |
| FORBIDDEN_DEPENDENCIES | any `frontend/src/modules/*`; any module API other than P00 |
| PUBLIC_INTERFACES | `frontend/src/shell/index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | see TESTS.md |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | backend modules, P00 shared code |

`frontend/package.json` changes (new npm deps) are a cross-module change once other frontend modules exist.
