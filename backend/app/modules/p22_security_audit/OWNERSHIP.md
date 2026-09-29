# P22 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P22 |
| MODULE_NAME | Security / Audit / Rollback |
| PURPOSE | Immutable cross-module action log with before/after values |
| OWNER_PATHS | `backend/app/modules/p22_security_audit/`, `backend/alembic/versions/0019_p22_security_audit.py`, `frontend/src/modules/security/`, `frontend/src/app/audit-log/` |
| OWNED_ROUTES | API `/api/v1/security/*` (read-only); UI `/audit-log` |
| OWNED_COMPONENTS | SecurityAuditPage |
| OWNED_SERVICES | record, query, facets |
| OWNED_TABLES | `audit_logs` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02 interface; shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py` (`record`); frontend `src/modules/security/index.ts` |
| FEATURE_FLAGS | none — always on, read-only |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p22_security_audit tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
