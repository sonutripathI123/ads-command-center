# Testing

## Layout
- **Module tests:** `backend/app/modules/<package>/tests/` — tag with `pytestmark = pytest.mark.module("PXX")`.
- **Isolation / governance tests:** `backend/tests/isolation/` — run on **every** change. They check:
  registry consistency, table ownership, import boundaries, shared→module imports, Google Ads mutation guard,
  route ownership, migration ownership + rollback notes + round-trip, and that generated docs are in sync.

## Commands
```bash
cd backend
python -m pytest -q                                      # everything
python -m pytest app/modules/p08_keyword_intel tests/isolation -q   # one module + isolation (normal change)
```

## Rules
- No network in tests. External APIs (Google Ads, GA4, Claude, crawler) are faked at the adapter interface.
- AI behaviour is tested with recorded fixtures (P23 provides the harness).
- Tests use a temporary SQLite DB (see `backend/conftest.py`); Postgres-specific behaviour gets an
  integration marker once needed.
- A change is not done until its module tests **and** `tests/isolation` pass.
