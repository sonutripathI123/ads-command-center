# Change Protocol (MID §5–§7, non-negotiable)

## For every change request

1. **Classify** — pick the MODULE_ID using the lookup table in [MODULE_REGISTRY.md](MODULE_REGISTRY.md).
2. **Scope** — read that module's `MODULE.md` and `OWNERSHIP.md`, then only the files that implement the
   behaviour and their direct dependencies (`interface.py` of dependencies, relevant `app/shared` file).
   Do **not** recursively read the repository.
3. **Plan** — before editing, state: target module, files likely to change and why, files explicitly not to change.
4. **Implement** — smallest possible patch.
5. **Verify** — run the module's tests plus the isolation suite:
   `cd backend && python -m pytest app/modules/<package> tests/isolation -q`
6. **Report** — use the response format below.
7. **Stop** — no refactors, redesigns, renames, reformatting or "clean-up" of anything else.

## Response format

```
Phase:
Module:
Requested change:
Files inspected:
Files changed:
Files not changed:        (protected modules/areas intentionally untouched)
Tests:
Dependencies changed:
Migration:
Risk:
Acceptance status:
```

Also append an entry to the module's `CHANGELOG.md`.

## Cross-module gate

If the change genuinely needs another module, **stop before editing it** and post:

```
CROSS-MODULE REQUEST
Target:                   PXX
Required dependency:      PYY
Reason:
Exact interface/dependency:
Files that must change:
Risk:                     LOW / MEDIUM / HIGH
Approval:                 REQUIRED
```

Prefer adapting the target module to an existing interface over changing the dependency.
The following always count as cross-module changes: any file in `app/shared/`, `app/main.py`,
`docs/modules.json`, `alembic/env.py`, `conftest.py`, `docker-compose.yml`.

## Protected behaviour

- Modules with status `approved_frozen` are only edited when the request explicitly targets them.
- No changes to unrelated UI, API contracts, tables, auth, execution permissions, prompts or business rules.
- No dependency upgrades, mass formatting or lint-only changes during feature work.
- No deleting working code because a rewrite is easier.
- No destructive migrations without explicit approval; never drop production data in feature work.
- No deployment after a local change.

## API changes

Response schemas in `schemas.py` are contracts. Adding optional fields is fine; removing/renaming fields or
changing types needs a new versioned route (`/api/v2/...`) and a migration plan.

## Migrations

`cd backend && python -m alembic revision -m "pNN: <what>"`, then set `module_id` and fill in the
rollback/recovery notes (the test suite rejects the template placeholders).
