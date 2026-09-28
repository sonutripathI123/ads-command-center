# P00 — Foundation & Governance

**Status:** approved_frozen (user approved 2026-09-23)

## Purpose
Repository structure, module boundaries, configuration/secrets, database + migrations, API/error/logging
conventions, feature flags, and the governance tests that keep every other module isolated.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p00_foundation/router.py` | read-only routes: health, modules, flags |
| `backend/app/modules/p00_foundation/schemas.py` | response contracts |
| `backend/app/modules/p00_foundation/interface.py` | public interface (empty; reusable code is in shared) |
| `backend/app/shared/*` | SHARED code — see MODULE_REGISTRY.md |
| `backend/app/shared/flags_cli.py` | operator CLI: list / set / clear flag overrides (not execution flags) |
| `backend/app/main.py` | app factory + auto-mount |
| `backend/alembic/` , `backend/alembic.ini` | migration framework |
| `backend/conftest.py`, `backend/pyproject.toml` | test bootstrap |
| `backend/tests/isolation/*` | governance/isolation tests |
| `docs/*`, `scripts/gen_registry.py`, `CLAUDE.md` | governance docs |
| `docker-compose.yml`, `backend/Dockerfile`, `.env.example` | environment |

## Routes
| Method | Path | Returns |
|---|---|---|
| GET | `/api/v1/foundation/health` | `{status, database, env, execution_kill_switch}` |
| GET | `/api/v1/foundation/modules` | registry entries |
| GET | `/api/v1/foundation/flags` | resolved flags `{key, module_id, enabled, source, description}` |

## Tables
`feature_flag_overrides` (model in `app/shared/feature_flags.py`, migration `0001_p00`).

## Acceptance criteria
- [x] Governance files from MID §3 exist; registry/dependency tables generated from `modules.json`.
- [x] All 25 modules registered with owner paths, tables, dependencies, flags.
- [x] Config from env; secrets typed `SecretStr`; prod refuses default secret key.
- [x] Alembic migrations with required `module_id` + rollback notes; upgrade/downgrade round-trip tested.
- [x] Standard error envelope, request-id propagation, JSON logs with module_id.
- [x] Feature flags: declared-only, default off, DB override, env kill switch beats override.
- [x] Isolation tests: import boundaries, shared purity, mutation guard, route + table ownership.
- [x] User review and approval (2026-09-23).
