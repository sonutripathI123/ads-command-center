# P00 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P00 |
| MODULE_NAME | Foundation & Governance |
| PURPOSE | Structure, conventions and guard-rails every other module builds on |
| OWNER_PATHS | `backend/app/modules/p00_foundation/`, `backend/app/shared/`, `backend/app/main.py`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic.ini`, `backend/conftest.py`, `backend/pyproject.toml`, `backend/requirements.txt`, `backend/Dockerfile`, `backend/tests/isolation/`, `docs/`, `scripts/`, `CLAUDE.md`, `README.md`, `docker-compose.yml`, `.env.example`, `.gitignore` |
| OWNED_ROUTES | `/api/v1/foundation/*` |
| OWNED_COMPONENTS | none (frontend starts in P01) |
| OWNED_SERVICES | settings, db session, logging, error handling, feature flags, registry loader |
| OWNED_TABLES | `feature_flag_overrides` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | none (third-party libs only) |
| FORBIDDEN_DEPENDENCIES | every `app/modules/*` package |
| PUBLIC_INTERFACES | see Shared code table in `docs/MODULE_REGISTRY.md` |
| FEATURE_FLAGS | none owned; owns the flag *system* |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p00_foundation tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | other modules' packages; Driver App repository |

Note: `alembic/versions/*` files are owned by the module named in each file's `module_id`, not by P00.
