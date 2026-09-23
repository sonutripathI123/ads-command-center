# P04 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P04 |
| MODULE_NAME | Google Ads Connection |
| PURPOSE | OAuth connection, account discovery/selection, connection health |
| OWNER_PATHS | `backend/app/modules/p04_ads_connection/`, `backend/alembic/versions/0003_p04_connections_ads_accounts.py`, `frontend/src/modules/ads-connection/`, `frontend/src/app/ads-accounts/` |
| OWNED_ROUTES | API `/api/v1/ads-connection/*`; UI `/ads-accounts` |
| OWNED_COMPONENTS | AdsAccountsPage |
| OWNED_SERVICES | OAuth, discovery, account registry, health check, read session |
| OWNED_TABLES | `connections`, `ads_accounts` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02 interface (auth); shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | `interface.py` (`active_accounts`, `open_read_session`, `ReadSession`, `AccountRef`); frontend `index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p04_ads_connection tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | P00, P01, P02 (frozen) |
