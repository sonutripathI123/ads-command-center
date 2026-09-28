# P05 Tests

```bash
cd backend && python -m pytest app/modules/p05_ads_sync tests/isolation -q
cd frontend && npm run lint && npm run build
```

`tests/conftest.py` replaces P04 (`active_accounts`, `open_read_session`) and P02 (`get_current_user`) through
their public interfaces with a `FakeAds` GAQL responder. `test_sync.py` covers: 90-day first window, 3-day
lookback, SELECT-only queries, totals/derived metrics, daily series, cost sorting, ad groups/keywords joins,
search-term summing across matched keywords, RSA text, idempotent re-sync, partial and failed runs, one run
at a time, viewer read-only, 404/422 cases, and the backend interface.
