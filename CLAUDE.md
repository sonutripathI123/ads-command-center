# AI Google Ads Specialist — Claude Code rules

The authoritative contract is [docs/MID.md](docs/MID.md). These rules summarise how to work in this repo.

## Every task
1. Classify the request to a MODULE_ID using the lookup table in `docs/MODULE_REGISTRY.md`.
2. Read that module's `MODULE.md` + `OWNERSHIP.md` first. Locate files through the registry —
   **do not recursively read the repository** for a local change.
3. Read only the files involved and direct dependencies (their `interface.py`, the relevant `app/shared` file).
4. State a short scope plan (target module, files to change + why, files not to change) before editing.
5. Make the smallest patch. No unrelated refactors, renames, formatting, redesigns or dependency upgrades.
6. Run `cd backend && python -m pytest app/modules/<package> tests/isolation -q`.
7. Append to the module's `CHANGELOG.md`; reply in the report format in `docs/CHANGE_PROTOCOL.md`; stop.

## Stop and ask (cross-module gate)
Before editing another module, any `backend/app/shared/` file, `backend/app/main.py`, `docs/modules.json`,
`alembic/env.py` or `conftest.py`, post the CROSS-MODULE REQUEST from `docs/CHANGE_PROTOCOL.md` and wait.

## Never, unless the request explicitly targets it and the user approves
- Enable Google Ads live execution, lift `ADS_EXECUTION_KILL_SWITCH`, or add mutate calls outside P17.
- Change auth, permissions, security settings, or an existing API response contract.
- Write destructive migrations or drop data.
- Deploy.
- Modify modules with status `approved_frozen`.
- Touch the Driver App repository (bookings are read via a P06 adapter only).

## Build mode ("build PXX")
Follow the build order in MID §21. One module at a time: implement → test → document → set status to `review`
in `docs/modules.json` → run `python scripts/gen_registry.py` → present the MID §22 acceptance checklist → stop.
Only the user moves a module to `approved_frozen`.
