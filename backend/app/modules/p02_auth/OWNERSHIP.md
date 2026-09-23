# P02 Ownership Contract

| Field | Value |
|---|---|
| MODULE_ID | P02 |
| MODULE_NAME | Authentication & User Access |
| PURPOSE | Sign-in, sessions, users, roles, permission checks |
| OWNER_PATHS | `backend/app/modules/p02_auth/`, `backend/alembic/versions/0002_p02_users_sessions.py`, `frontend/src/modules/auth/`, `frontend/src/app/login/`, `frontend/src/app/account/`, `frontend/src/proxy.ts` |
| OWNED_ROUTES | API `/api/v1/auth/*`; UI `/login`, `/account` |
| OWNED_COMPONENTS | LoginForm, AccountPanel, UsersAdmin |
| OWNED_SERVICES | login, session resolution, user management, CLI |
| OWNED_TABLES | `users`, `sessions` |
| OWNED_PROMPTS | none |
| ALLOWED_DEPENDENCIES | shared (P00) only |
| FORBIDDEN_DEPENDENCIES | every other module |
| PUBLIC_INTERFACES | backend `interface.py`; frontend `src/modules/auth/index.ts` (+ `constants.ts` for `proxy.ts`) |
| FEATURE_FLAGS | none |
| TEST_COMMANDS | `cd backend && python -m pytest app/modules/p02_auth tests/isolation -q` |
| ACCEPTANCE_CRITERIA | see MODULE.md |
| DO_NOT_TOUCH | P00, P01 (frozen); P17 execution logic |
