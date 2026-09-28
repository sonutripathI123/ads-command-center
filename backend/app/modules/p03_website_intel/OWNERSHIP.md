# P03 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P03 |
| MODULE_NAME | Website Intelligence |
| PURPOSE | Websites, crawling, page signals, landing-page mapping |
| OWNER_PATHS | `backend/app/modules/p03_website_intel/`, `backend/alembic/versions/0007_p03_websites.py`, `frontend/src/modules/websites/`, `frontend/src/app/websites/` |
| OWNED_ROUTES | API `/api/v1/websites*`; UI `/websites`, `/websites/[id]` |
| OWNED_COMPONENTS | WebsitesPage, WebsiteForm, WebsiteDetail |
| OWNED_SERVICES | crawler, extraction, landing-page mapping |
| OWNED_TABLES | `websites`, `pages`, `crawl_runs`, `page_signals`, `landing_page_mappings` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P05, P21 interfaces; shared (incl. feature flags) |
| FORBIDDEN_DEPENDENCIES | all other modules; crawling any domain that is not a registered website |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/websites/index.ts` |
| FEATURE_FLAGS | `crawler.enabled` (default off) |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p03_website_intel tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
