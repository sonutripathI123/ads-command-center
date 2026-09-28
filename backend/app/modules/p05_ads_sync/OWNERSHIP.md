# P05 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P05 |
| MODULE_NAME | Google Ads Data Sync & Warehouse |
| PURPOSE | Local copy of Google Ads entities + daily metrics; performance queries |
| OWNER_PATHS | `backend/app/modules/p05_ads_sync/`, `backend/alembic/versions/0004_p05_ads_warehouse.py`, `frontend/src/modules/ads-sync/`, `frontend/src/app/campaigns/`, `frontend/src/app/ad-groups/`, `frontend/src/app/keywords/`, `frontend/src/app/search-terms/` |
| OWNED_ROUTES | API `/api/v1/ads-sync/*`; UI `/campaigns`, `/ad-groups`, `/keywords`, `/search-terms` (P08 will extend the last two via a change request) |
| OWNED_COMPONENTS | AdsDataFrame, DataTable, SpendChart, Campaigns/AdGroups/Keywords/SearchTerms pages |
| OWNED_SERVICES | sync engine, aggregations |
| OWNED_TABLES | `campaigns`, `ad_groups`, `keywords`, `search_terms`, `ads`, `metrics_snapshots`, `sync_runs` (`ad_assets` reserved) |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02 interface (auth), P04 interface (accounts, read session); shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/ads-sync/index.ts` |
| FEATURE_FLAGS | `ads_sync.scheduled.enabled` (declared; scheduler not built) |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p05_ads_sync tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | P00, P01, P02, P04 (frozen) |
