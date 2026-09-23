# P04 Tests

```bash
cd backend && python -m pytest app/modules/p04_ads_connection tests/isolation -q
cd frontend && npm run lint && npm run build
```

All Google traffic goes to `FakeGoogle` (httpx.MockTransport) in `tests/conftest.py`, which also fails the test if
any mutate URL is called. `test_ads_connection.py` covers: auth/permissions, OAuth start params + nonce cookie,
encrypted storage, forged/missing state, user-denied, no refresh token, manager discovery, add via manager, bad ID,
permission-denied surfacing, health check incl. deleted OAuth client, disconnect/revoke, config errors,
`ReadSession` interface, SELECT-only guard.
