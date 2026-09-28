# P00 Changelog

## 2026-09-23 — initial build
- Created repository structure, governance docs, machine-readable registry for P00–P24.
- Shared config/db/logging/errors/feature-flags/registry; app factory with auto-mounted module routers.
- Alembic framework + migration `0001_p00` (feature_flag_overrides).
- Isolation/governance test suite.
- Status: `review`.

## 2026-09-28 — approved cross-module change (requested by P03)
- `app/shared/flags_cli.py`: `list`, `set KEY on|off --reason ... [--by ...]`, `clear KEY`. Server-side only.
  Refuses unknown keys and every kill-switch-guarded (execution) flag. Tests: `tests/test_flags_cli.py`.
