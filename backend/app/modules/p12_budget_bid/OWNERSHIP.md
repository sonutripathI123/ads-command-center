# P12 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P12 |
| MODULE_NAME | Budget / Bid / Geo / Device / Time Intelligence |
| PURPOSE | Read-only segment analysis (device, day, time, location, budget) with plain-language findings |
| OWNER_PATHS | `backend/app/modules/p12_budget_bid/`, `backend/alembic/versions/0021_p12_budget_bid.py`, `frontend/src/modules/budget-bid/`, `frontend/src/app/budget-bid/` |
| OWNED_ROUTES | API `/api/v1/budget-bid/*`; UI `/budget-bid` |
| OWNED_COMPONENTS | BudgetBidPage |
| OWNED_SERVICES | gaql pull, analysis, run, latest |
| OWNED_TABLES | `segment_runs`, `segment_findings` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P04 (read session), P21 interfaces; shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py` (`segment_findings`); frontend `src/modules/budget-bid/index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p12_budget_bid tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
