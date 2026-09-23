# Architecture (approved: P00)

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js + TypeScript | scaffolded in P01; one folder per module under `frontend/src/modules/` |
| Backend | FastAPI (Python 3.12+) | modular monolith: one package per MODULE_ID |
| Database | PostgreSQL 16 | SQLAlchemy 2.0 ORM, Alembic migrations; SQLite only for tests |
| Jobs | Redis + worker/scheduler | introduced with P05 (sync) — library decision recorded in DECISIONS.md then |
| AI | Claude API | via a P14-owned adapter; fixture mode unless `ai.live_calls.enabled` |
| Advertising | Google Ads API | read adapter in P04/P05; mutation client **only** in P17 |
| Analytics | GA4, Search Console | P06 / P03 adapters |
| Bookings | Driver App (existing system) | read-only adapter in P06; Driver App is never modified by this project |
| Auth | Google OAuth 2.0 | P02 |

## Request flow

```
Browser ─► Next.js (P01 shell + module pages) ─► /api/v1/<module-slug>/…  ─► module router
                                                                              │
                                                    module service ─► module models (own tables)
                                                                   ─► other module's interface.py (declared deps only)
                                                                   ─► app/shared (config, db, flags, logging, errors)
```

## Conventions

- **Routes:** `/api/v1/<slug>/...` where slug and prefix come from `modules.json`. Mounted automatically.
- **Errors:** raise `AppError` subclasses with `module_id`; clients always get
  `{"error": {code, message, module_id, request_id, details}}`.
- **Logging:** `log = get_logger("PXX")`; JSON lines with `module_id` and `request_id`.
- **Flags:** declare in `modules.json`, check with `is_enabled(key, db)` / `require_enabled(...)`.
  All flags default off. Unknown flag keys raise.
- **Execution safety:** `ADS_EXECUTION_KILL_SWITCH=true` (env) forces every execution flag off,
  regardless of DB state. Lifting it requires an environment change by an operator **and** a DB override.
- **Money/time:** store money as integer cents + currency (AUD default); timestamps as UTC `timestamptz`,
  display in each website's timezone (set in P03; default `Australia/Sydney`).
