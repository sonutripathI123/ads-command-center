# P17 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P17 |
| MODULE_NAME | Google Ads Execution |
| PURPOSE | Validate / apply / roll back P16-approved Google Ads changes, behind kill switch + flag + permission |
| OWNER_PATHS | `backend/app/modules/p17_ads_execution/`, `backend/alembic/versions/0020_p17_ads_execution.py`, `frontend/src/modules/execution/`, `frontend/src/app/execution/` |
| OWNED_ROUTES | API `/api/v1/execution/*`; UI `/execution` |
| OWNED_COMPONENTS | ExecutionPage |
| OWNED_SERVICES | plans, google (mutate calls), validate, execute, rollback, operator CLI |
| OWNED_TABLES | `executions` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P04, P05, P09, P16, P22 interfaces; shared |
| FORBIDDEN_DEPENDENCIES | all other modules |
| PUBLIC_INTERFACES | backend `interface.py` (`execution_status`, `recent_executions`); frontend `src/modules/execution/index.ts` |
| FEATURE_FLAGS | `ads.execution.enabled`, `ads.execution.automation.enabled` (both default off, kill-switch guarded) |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p17_ads_execution tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules, except the one additive P04 interface function listed in CHANGELOG.md |
