# P24 Tests

```bash
cd backend && python -m pytest app/modules/p24_hardening tests/isolation -q
```
`tests/test_p24.py`: in-memory counter windowing; Redis fallback when unreachable; rate-limit middleware blocks
after the limit and never blocks an exempt path; security headers present (HSTS only when enabled); `with_retry`
succeeds after transient errors, re-raises after exhausting attempts, and never catches a non-listed exception;
`install(app)` adds security headers and does **not** rate-limit inside the test suite (`APP_ENV=test`); the
smoke script's own check function against our real app (`create_app()` via an in-process ASGI transport) —
health/me pass, a made-up path correctly fails.
