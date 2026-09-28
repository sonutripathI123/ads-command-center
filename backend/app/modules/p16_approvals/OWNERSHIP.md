# P16 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P16 |
| MODULE_NAME | Approval Center |
| PURPOSE | Human approval queue for every proposed Google Ads change |
| OWNER_PATHS | `backend/app/modules/p16_approvals/`, `backend/alembic/versions/0013_p16_approvals.py`, `frontend/src/modules/approvals/`, `frontend/src/app/approvals/` |
| OWNED_ROUTES | API `/api/v1/approvals/*`; UI `/approvals` |
| OWNED_COMPONENTS | ApprovalsPage, ApprovalCard |
| OWNED_SERVICES | queue sync, decisions, history |
| OWNED_TABLES | `approvals`, `approval_events` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02, P05, P08, P09, P14, P15 interfaces (P22 audit when built); shared |
| FORBIDDEN_DEPENDENCIES | all other modules; any Google Ads mutate API |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/approvals/index.ts` |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p16_approvals tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
