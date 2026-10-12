# P23 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P23 |
| MODULE_NAME | Testing & QA |
| PURPOSE | Shared QA harness (API mocks, recorded AI fixtures) and product-wide route/permission/lock audits |
| OWNER_PATHS | `backend/app/modules/p23_testing_qa/` |
| OWNED_ROUTES | none |
| OWNED_COMPONENTS | none |
| OWNED_SERVICES | audit_anonymous, audit_read_only_writes, list_routes, FakeClaude, FakeAdsAPI, load_fixture |
| OWNED_TABLES | none |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02 interface; shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads API; any network call |
| PUBLIC_INTERFACES | backend `interface.py` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p23_testing_qa tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
