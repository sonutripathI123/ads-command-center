# P10 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P10 |
| MODULE_NAME | Landing Page & CRO Intelligence |
| PURPOSE | Check ad landing pages for conversion issues; write implementation briefs |
| OWNER_PATHS | `backend/app/modules/p10_landing_cro/`, `backend/alembic/versions/0015_p10_landing_cro.py`, `frontend/src/modules/landing-pages/`, `frontend/src/app/landing-pages/` |
| OWNED_ROUTES | API `/api/v1/landing-pages/*`; UI `/landing-pages` |
| OWNED_COMPONENTS | LandingPagesPage, PageCard, BriefView |
| OWNED_SERVICES | fetch, extract, rules, brief |
| OWNED_TABLES | `landing_page_checks`, `cro_findings`, `implementation_briefs` |
| OWNED_PROMPTS | `brief.SYSTEM` (implementation brief) |
| ALLOWED_DEPENDENCIES | P02, P03, P05, P06, P21 interfaces; shared (flags `crawler.enabled` of P03 and `ai.live_calls.enabled` of P14, read-only) |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API; writing to websites |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/landing-pages/index.ts` |
| FEATURE_FLAGS | none of its own |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p10_landing_cro tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
