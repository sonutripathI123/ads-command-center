# P18 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P18 |
| MODULE_NAME | Monitoring & Alerts |
| PURPOSE | Account checks, deduplicated alerts, scheduled runs |
| OWNER_PATHS | `backend/app/modules/p18_monitoring/`, `backend/alembic/versions/0017_p18_monitoring.py`, `frontend/src/modules/monitoring/`, `frontend/src/app/monitoring/` |
| OWNED_ROUTES | API `/api/v1/monitoring/*`; UI `/monitoring` |
| OWNED_COMPONENTS | MonitoringPage, AlertCard |
| OWNED_SERVICES | checks, run, run_scheduled |
| OWNED_TABLES | `alerts`, `monitor_checks` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P03, P05, P06 interfaces; shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/monitoring/index.ts` |
| FEATURE_FLAGS | `monitoring.scheduled.enabled` (default off) |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p18_monitoring tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
