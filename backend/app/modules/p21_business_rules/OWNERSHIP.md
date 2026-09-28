# P21 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P21 |
| MODULE_NAME | Business Memory & Rules |
| PURPOSE | Versioned business rules for analysis |
| OWNER_PATHS | `backend/app/modules/p21_business_rules/`, `backend/alembic/versions/0005_p21_business_rules.py`, `frontend/src/modules/business-rules/`, `frontend/src/app/business-rules/` |
| OWNED_ROUTES | API `/api/v1/business-rules*`; UI `/business-rules` |
| OWNED_COMPONENTS | RulesPage |
| OWNED_SERVICES | rules versioning |
| OWNED_TABLES | `business_rules`, `business_rule_versions` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | P02 interface; shared |
| FORBIDDEN_DEPENDENCIES | all other modules |
| PUBLIC_INTERFACES | `interface.py` (`Rules`, `get_rules`) |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p21_business_rules tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | frozen modules |
