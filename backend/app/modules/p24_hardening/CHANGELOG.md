# P24 Changelog

## 2026-09-30 — initial build

**CROSS-MODULE CHANGES** (per docs/CHANGE_PROTOCOL.md — declared here since `app/main.py` and
`docs/modules.json` are always cross-module):

- `app/main.py` (P00, `approved_frozen`): added one line, `p24_hardening.install(app)`, right after
  `register_error_handlers(app)` in `create_app()`. Nothing else in the file changed. Risk: LOW — additive only,
  and rate limiting is a no-op whenever `APP_ENV=test` (see `interface.install`), so it cannot affect any
  existing module's test suite.
- `docs/modules.json`: P24 status `planned` → `review`; added `"P24"` to the `depends_on` of P09, P10, P11, P14
  (each now imports `p24_hardening.interface.with_retry` around its Claude API call).
- P09 `writer.py`, P10 `brief.py`, P11 `interpret.py`, P14 `ai.py`: wrapped only the
  `client.beta.messages.create(...)` call in `with_retry(..., retry_on=(anthropic.APIConnectionError,
  anthropic.RateLimitError, anthropic.InternalServerError))` — up to 3 attempts with exponential backoff before
  the existing (unchanged) error handling below it runs. No other line in any of these four files changed.

**Not done in this pass** (deferred, needs its own cross-module request):
- P04 (Google Ads read adapter) and P06 (GA4/Search Console adapters) are `approved_frozen` and make their own
  external network calls without retry. Wrapping them the same way is straightforward but wasn't done here to
  keep this change's blast radius to modules already in `review`. Flagging for a future CR-P24-1.

**New (P24's own code):**
- `rate_limit.py`: per-client-IP fixed-window limiter (default 300 req/min), Redis-backed when `REDIS_URL` is
  reachable, in-memory fallback otherwise; off during tests; `/api/v1/foundation/health` is exempt.
- `security_headers.py`: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and HSTS in production.
- `retry.py`: generic `with_retry()` backoff wrapper.
- `smoke.py`: standalone post-deploy smoke test script (no DB/app import — plain HTTP against a running instance).
- `scripts/backup.sh`, `docs/RUNBOOK.md`: backup + recovery documentation.
