# P08 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P08 |
| MODULE_NAME | Keyword & Search-Term Intelligence |
| PURPOSE | Search-term intent, negative keyword suggestions, keyword insights |
| OWNER_PATHS | `backend/app/modules/p08_keyword_intel/`, `backend/alembic/versions/0006_p08_keyword_intel.py`, `frontend/src/modules/keyword-intel/`, `frontend/src/app/search-terms/negatives/`, `frontend/src/app/keywords/insights/` |
| OWNED_ROUTES | API `/api/v1/keywords/*`; UI `/search-terms/negatives`, `/keywords/insights` |
| OWNED_COMPONENTS | NegativesPage, InsightsPage |
| OWNED_SERVICES | analysis, review, export |
| OWNED_TABLES | `search_term_classifications`, `negative_keyword_candidates`, `keyword_candidates` |
| OWNED_PROMPTS | none yet (P14) |
| ALLOWED_DEPENDENCIES | P02, P05, P21 interfaces (P14 allowed, unused); shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/keyword-intel/index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p08_keyword_intel tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules; P05 pages except the two links |
