# P00 Tests

```bash
cd backend
python -m pytest app/modules/p00_foundation tests/isolation -q
```

| File | Covers |
|---|---|
| `tests/test_foundation_api.py` | health, request id, modules list, flags list, no write endpoint, error envelope, 500 hygiene |
| `tests/test_feature_flags.py` | unknown flag, default, DB override, kill switch precedence, require_enabled, secret repr |
| `../../../tests/isolation/test_registry.py` | registry integrity, acyclic deps, single table owner, only P17 mutates |
| `../../../tests/isolation/test_module_boundaries.py` | package/doc presence, import boundaries, shared purity, mutation guard, route/table ownership |
| `../../../tests/isolation/test_migrations.py` | module_id + rollback notes, upgrade/downgrade round-trip |
| `../../../tests/isolation/test_docs_sync.py` | governance files exist, generated tables in sync |
