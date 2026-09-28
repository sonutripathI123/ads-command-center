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

## Errors
- Unhandled exceptions return a generic 500 with request_id; stack traces go to logs only.

## Open items (owned by later modules)
- P02: session security, RBAC (read / recommend / execute; execute off by default).
- P22: immutable audit log with before/after values; rollback procedures.
- P24: rate limiting, dependency scanning, security review.
