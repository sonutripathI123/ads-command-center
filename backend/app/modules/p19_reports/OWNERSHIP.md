# P19 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P19 |
| MODULE_NAME | Reports & Exports |
| PURPOSE | Account/website reports, snapshots, CSV and print/PDF exports |
| OWNER_PATHS | `backend/app/modules/p19_reports/`, `backend/alembic/versions/0018_p19_reports.py`, `frontend/src/modules/reports/`, `frontend/src/app/reports/` |
| OWNED_ROUTES | API `/api/v1/reports/*`; UI `/reports` |
| OWNED_COMPONENTS | ReportsPage, ReportView |
| OWNED_SERVICES | builder, render |
| OWNED_TABLES | `report_runs` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P03, P05, P06, P13, P14, P16, P18 interfaces; shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/reports/index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p19_reports tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
