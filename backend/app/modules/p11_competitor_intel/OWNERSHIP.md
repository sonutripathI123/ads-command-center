# P11 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P11 |
| MODULE_NAME | Competitor Intelligence |
| PURPOSE | Public competitor research, coverage gaps, labelled interpretation |
| OWNER_PATHS | `backend/app/modules/p11_competitor_intel/`, `backend/alembic/versions/0016_p11_competitor_intel.py`, `frontend/src/modules/competitors/`, `frontend/src/app/competitors/` |
| OWNED_ROUTES | API `/api/v1/competitors/*`; UI `/competitors` |
| OWNED_COMPONENTS | CompetitorsPage, CompetitorCard, CoverageTable, InterpretationView |
| OWNED_SERVICES | research, analysis, interpret |
| OWNED_TABLES | `competitors`, `competitor_observations`, `competitor_analyses` |
| OWNED_PROMPTS | `interpret.SYSTEM` |
| ALLOWED_DEPENDENCIES | P02, P03, P05, P21 interfaces; shared (flag `ai.live_calls.enabled` of P14, read-only) |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API; scraping search-engine result pages |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/competitors/index.ts` |
| FEATURE_FLAGS | `competitor.research.enabled` (default off) |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p11_competitor_intel tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
