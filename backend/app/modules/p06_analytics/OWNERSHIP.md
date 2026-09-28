# P06 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P06 |
| MODULE_NAME | Analytics & Conversion Data |
| PURPOSE | GA4, Search Console, conversion mapping, bookings, tracking health |
| OWNER_PATHS | `backend/app/modules/p06_analytics/`, `backend/alembic/versions/0008_p06_analytics.py`, `frontend/src/modules/conversions/`, `frontend/src/app/conversions/` |
| OWNED_ROUTES | API `/api/v1/conversions/*`; UI `/conversions` |
| OWNED_COMPONENTS | ConversionsPage |
| OWNED_SERVICES | analytics sync, health checks, bookings import |
| OWNED_TABLES | `analytics_daily`, `conversion_events`, `search_console_daily`, `conversion_mappings`, `analytics_sync_runs`, `bookings` (+ reserved `leads`, `quotes`, `revenue_records`) |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P03, P05 interfaces; shared |
| FORBIDDEN_DEPENDENCIES | all other modules; storing customer personal data |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/conversions/index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p06_analytics tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules; the Driver App repository |
