# P15 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P15 |
| MODULE_NAME | AI Campaign Builder |
| PURPOSE | Draft, paused, themed campaigns from existing keywords |
| OWNER_PATHS | `backend/app/modules/p15_campaign_builder/`, `backend/alembic/versions/0012_p15_campaign_drafts.py`, `frontend/src/modules/campaign-builder/`, `frontend/src/app/campaign-builder/` |
| OWNED_ROUTES | API `/api/v1/campaign-builder/*`; UI `/campaign-builder` |
| OWNED_COMPONENTS | BuilderPage, BuildForm, DraftView |
| OWNED_SERVICES | builder, edit ops, export |
| OWNED_TABLES | `campaign_drafts` |
| OWNED_PROMPTS | none (ad copy prompts are P09's) |
| ALLOWED_DEPENDENCIES | P02, P03, P05, P06, P08, P09, P21 interfaces; shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/campaign-builder/index.ts` |
| FEATURE_FLAGS | none (AI via P09) |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p15_campaign_builder tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
