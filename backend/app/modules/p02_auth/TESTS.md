# P02 Tests

```bash
cd backend && python -m pytest app/modules/p02_auth tests/isolation -q
cd frontend && npm run lint && npm run build
```

| File | Covers |
|---|---|
| `tests/test_auth.py` | hashing, login cookie flags, token stored hashed, no user enumeration, throttle, inactive user, expiry, logout, origin check, `require_permission`, execute switch |
| `tests/test_users_admin.py` | admin-only access, create/list, validation, execute not grantable via API, last-admin protection, deactivation kills sessions |
| `tests/conftest.py` | creates P02 tables, cleans users/sessions between tests |
