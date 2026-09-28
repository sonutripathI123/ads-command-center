# P20 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P20 |
| MODULE_NAME | Experiments |
| PURPOSE | A/B and before/after tests measured from synced data |
| OWNER_PATHS | `backend/app/modules/p20_experiments/`, `backend/alembic/versions/0014_p20_experiments.py`, `frontend/src/modules/experiments/`, `frontend/src/app/experiments/` |
| OWNED_ROUTES | API `/api/v1/experiments/*`; UI `/experiments` |
| OWNED_COMPONENTS | ExperimentsPage, ExperimentForm, ResultsView |
| OWNED_SERVICES | lifecycle, analysis (stats) |
| OWNED_TABLES | `experiments` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P03, P05, P06, P16 interfaces; shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/experiments/index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p20_experiments tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
