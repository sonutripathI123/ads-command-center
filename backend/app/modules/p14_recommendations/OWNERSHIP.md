# P14 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P14 |
| MODULE_NAME | AI Recommendation Engine |
| PURPOSE | Standard recommendations + AI action plan |
| OWNER_PATHS | `backend/app/modules/p14_recommendations/`, `backend/alembic/versions/0010_p14_recommendations.py`, `frontend/src/modules/recommendations/`, `frontend/src/app/recommendations/` |
| OWNED_ROUTES | API `/api/v1/recommendations/*`; UI `/recommendations` |
| OWNED_COMPONENTS | RecommendationsPage |
| OWNED_SERVICES | ingest, prioritisation, decisions, AI plan |
| OWNED_TABLES | `recommendations`, `ai_runs`, `ai_evidence` |
| OWNED_PROMPTS | `ai.py` SYSTEM + PLAN_SCHEMA |
| ALLOWED_DEPENDENCIES | P02, P05, P07, P21 interfaces (P22 allowed, not built); shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/recommendations/index.ts` |
| FEATURE_FLAGS | `ai.live_calls.enabled` (default off) |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p14_recommendations tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
