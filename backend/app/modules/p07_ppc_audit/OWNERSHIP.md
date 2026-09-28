# P07 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P07 |
| MODULE_NAME | PPC Audit Engine |
| PURPOSE | Evidence-backed account audit and health score |
| OWNER_PATHS | `backend/app/modules/p07_ppc_audit/`, `backend/alembic/versions/0009_p07_audit.py`, `frontend/src/modules/audit/`, `frontend/src/app/audit/` |
| OWNED_ROUTES | API `/api/v1/audit/*`; UI `/audit` |
| OWNED_COMPONENTS | AuditPage |
| OWNED_SERVICES | audit run, checks, dismissals |
| OWNED_TABLES | `audit_runs`, `audit_issues` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P03, P05, P06, P08, P21 interfaces (P14 allowed, unused); shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/audit/index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p07_ppc_audit tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
