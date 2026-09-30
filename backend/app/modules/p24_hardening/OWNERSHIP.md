# P24 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P24 |
| MODULE_NAME | Production Hardening |
| PURPOSE | Rate limits, retries, security headers, smoke tests, backups, recovery docs |
| OWNER_PATHS | `backend/app/modules/p24_hardening/`, `scripts/backup.sh`, `docs/RUNBOOK.md` |
| OWNED_ROUTES | none (no api_prefix; middleware only) |
| OWNED_COMPONENTS | none (no frontend page) |
| OWNED_SERVICES | with_retry, install (rate-limit + security-header middleware) |
| OWNED_TABLES | none |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | `app/shared` (config, logging) |
| FORBIDDEN_DEPENDENCIES | all feature modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py` (`with_retry`, `install`) |
| FEATURE_FLAGS | none — rate limiting/security headers are always on outside tests |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p24_hardening tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules, except the single additive line in `app/main.py` documented in CHANGELOG.md |
