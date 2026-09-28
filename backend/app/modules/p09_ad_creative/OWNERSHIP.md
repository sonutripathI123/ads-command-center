# P09 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P09 |
| MODULE_NAME | Ad & Creative Intelligence |
| PURPOSE | RSA analysis, AI copy, claim/policy checks, drafts |
| OWNER_PATHS | `backend/app/modules/p09_ad_creative/`, `backend/alembic/versions/0011_p09_ad_creative.py`, `frontend/src/modules/creatives/`, `frontend/src/app/ads-assets/` |
| OWNED_ROUTES | API `/api/v1/creatives/*`; UI `/ads-assets` |
| OWNED_COMPONENTS | CreativesPage, ExistingAds, Writer, Drafts, DraftEditor |
| OWNED_SERVICES | analysis, writer, checks, export |
| OWNED_TABLES | `ad_drafts`, `claim_checks` |
| OWNED_PROMPTS | `writer.py` SYSTEM + SCHEMA |
| ALLOWED_DEPENDENCIES | P02, P05, P21 interfaces; shared (reads flag `ai.live_calls.enabled`) |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/creatives/index.ts` |
| FEATURE_FLAGS | uses `ai.live_calls.enabled` (owned by P14) |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p09_ad_creative tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
