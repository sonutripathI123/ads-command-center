# Security

## Secrets
- All secrets come from environment variables (`backend/.env` locally, never committed; see `.env.example`).
- Typed as `SecretStr` in `app/shared/config.py` — they do not appear in reprs or logs.
- Production refuses to start with the default `APP_SECRET_KEY`.
- OAuth refresh tokens for Google Ads/GA4 (P02/P04) will be stored encrypted at rest; never sent to the browser.

## Execution safety (MID §16)
| Level | Scope | Status |
|---|---|---|
| 0 Read only | audit, reports, analysis | allowed |
| 1 Draft | keywords, ads, campaign plans | allowed (stored locally only) |
| 2 Approval required | keyword/negative/ad/campaign/budget/bid changes | P16 approval record + P17 flag |
| 3 High-impact approval | major budget, bid strategy, structural | P16 second confirmation + P17 flag |
| 4 Automation | allowlisted low-risk ops | **disabled** (`ads.execution.automation.enabled`) |

Controls already enforced in P00:
- `ADS_EXECUTION_KILL_SWITCH` env var (default `true`) overrides every kill-switch-guarded flag.
- No API endpoint can change flags. Operators use `python -m app.shared.flags_cli` on the server (reason + who stored);
  it refuses execution (kill-switch-guarded) flags.
- Test: only P17 code may contain Google Ads mutate calls.
- New campaigns default to draft/paused (enforced in P15/P17).

## Audit trail (P22)
- `audit_logs` (append-only, no edit/delete endpoint): who did what, before/after values. `interface.record(...)` is
  the only write path. Admin-only read API at `/api/v1/security/audit-logs` (filters: module, actor, action, entity,
  date range) and the "Audit Log" page.
- Wired in so far: P16 approval decisions (approve/reject/withdraw/execute), P09 ad draft review (approved/rejected).
- Rollback/compensation procedures are deferred until P17 executes anything against Google Ads — nothing to
  compensate for yet.

## Production hardening (P24)
- Rate limiting: per-client-IP fixed window (default 300 req/min), Redis-backed when reachable, in-memory
  fallback otherwise. Off during the test suite (`APP_ENV=test`) so it can never affect test runs.
- Security headers on every response: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, plus HSTS
  when `APP_ENV=production`.
- Retries with exponential backoff (`with_retry`) around the Claude API call in P09/P10/P11/P14 — a transient
  network blip or momentary 5xx/429 no longer fails the whole request.
- Deployment, backups, smoke tests and the recovery runbook: see `docs/DEPLOY.md` and `docs/RUNBOOK.md`.

## Errors
- Unhandled exceptions return a generic 500 with request_id; stack traces go to logs only.

## Open items (owned by later modules)
- P02: session security, RBAC (read / recommend / execute; execute off by default).
- P22: rollback/compensation procedures (once P17 exists).
- P24: retries for P04 (Google Ads) / P06 (GA4/Search Console) external calls; formal dependency scanning.
