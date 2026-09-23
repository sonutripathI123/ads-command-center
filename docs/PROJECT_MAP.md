# Project Map

```
ads-command-center/
├── CLAUDE.md                     ← operating rules for Claude Code (read automatically)
├── docs/
│   ├── MID.md                    ← authoritative build contract
│   ├── modules.json              ← machine-readable module registry (SOURCE OF TRUTH)
│   ├── MODULE_REGISTRY.md        ← feature → module → files  (tables generated)
│   ├── DEPENDENCY_MAP.md         ← allowed dependencies      (tables generated)
│   ├── CHANGE_PROTOCOL.md        ← how to make an isolated change
│   ├── ARCHITECTURE.md  SECURITY.md  TESTING.md  DECISIONS.md
├── scripts/gen_registry.py       ← regenerates registry/dependency tables
├── backend/                      ← FastAPI (Python)
│   ├── app/main.py               ← SHARED app factory, auto-mounts module routers
│   ├── app/shared/               ← SHARED (owner P00): config, db, errors, logging, flags, registry
│   ├── app/modules/pNN_<name>/   ← one package per module (see below)
│   ├── alembic/versions/         ← migrations; each declares module_id
│   └── tests/isolation/          ← governance + boundary tests (run on every change)
├── frontend/                     ← Next.js + TypeScript (scaffolded in P01)
└── docker-compose.yml            ← postgres, redis, backend
```

## Anatomy of a backend module

```
backend/app/modules/p08_keyword_intel/
├── MODULE.md       purpose, files, routes, tables, flags, acceptance criteria
├── OWNERSHIP.md    MID §4 ownership contract
├── TESTS.md        how to test this module
├── CHANGELOG.md    one entry per change request
├── interface.py    the ONLY file other modules may import
├── router.py       FastAPI router (mounted at api_prefix from modules.json)
├── schemas.py      request/response contracts
├── service.py      business logic
├── models.py       SQLAlchemy models for tables this module owns
├── prompts/        AI prompts owned by this module
├── adapters/       external API adapters owned by this module
└── tests/
```

Only files a module actually needs are created. New module = add package + set status in `modules.json`
to `in_progress`; the router is mounted automatically and `main.py` is not edited.
