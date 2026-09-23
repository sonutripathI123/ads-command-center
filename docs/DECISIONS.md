# Architecture Decisions

## ADR-001 — Separate repository from Driver App (2026-09-23, accepted)
The Ads Specialist lives in its own repo. Booking/revenue data is read from Driver App through a read-only
adapter owned by P06, so Driver App's code, database and deployment are never touched by this project.

## ADR-002 — Modular monolith with a machine-readable registry (2026-09-23, accepted)
One FastAPI app; one package per MODULE_ID. `docs/modules.json` is the single source of truth for
ownership, dependencies, tables, routes and flags. Human docs are generated from it, and tests enforce it,
so the registry cannot silently drift from the code.

## ADR-003 — Routers auto-mounted from the registry (2026-09-23, accepted)
Adding a module never edits `main.py` (shared). Modules with status `planned` are not mounted.

## ADR-004 — Kill switch is environment-level (2026-09-23, accepted)
`ADS_EXECUTION_KILL_SWITCH` is read from the environment and beats any DB flag state, so a compromised or
buggy admin path cannot enable live Google Ads mutations on its own.

## ADR-005 — SQLite for tests, Postgres everywhere else (2026-09-23, accepted)
Keeps the test suite dependency-free and fast. Postgres-only features get integration-marked tests.

## Open questions (for user decision before the relevant phase)
- **Build order vs. dependencies.** P07–P13 depend on P14 (recommendation schema) and P21 (business rules),
  which the MID schedules later. Proposal: build P21 and the P14 *schema/contract* right after P06,
  or have P07–P13 emit P14-shaped records via P14's interface once it exists. Decide before P07.
- **P01 frontend location.** Next.js per MID; confirm hosting (same VPS as Driver App vs separate).
- **Job runner library** (RQ / Arq / Celery) — decide at P05.
