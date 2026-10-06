# P24 — Production Hardening

**Status:** approved_frozen (user approved 2026-10-06)

## Purpose
MID §11 P24 lists: deployment, backups, monitoring, retries, rate limits, API quota handling, security review,
smoke tests, recovery documentation. This module is the net-new backend code for **rate limits** and **retries**;
the rest (deployment, backups, smoke tests, recovery docs) are scripts/docs that live outside a single module's
Python package — see the table below for where each piece actually is.

## What's here vs. what's elsewhere
| MID §11 item | Where |
|---|---|
| Rate limits | `rate_limit.py` — fixed-window counter per client IP, Redis-backed when reachable, in-memory fallback. Wired globally via `interface.install(app)`. **Off during tests** (`APP_ENV=test`) so it never interferes with the test suite. |
| Retries | `retry.py` — `with_retry()`, a small backoff wrapper. Applied to the Claude API call in P09/P10/P11/P14 (the only external calls this module touches — see CHANGELOG for why P04/P06 aren't wrapped yet). |
| API quota handling | Already-existing `anthropic.RateLimitError` handling in P09/P10/P11/P14 now retries first (up to 3 attempts, exponential backoff) before surfacing the existing "try again in a minute" error. |
| Security review | `security_headers.py` — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS in production. Wired the same way. |
| Deployment | `docker-compose.prod.yml`, `frontend/Dockerfile`, `deploy/Caddyfile`, `.env.production.example`, `docs/DEPLOY.md` (added in the previous change). |
| Backups | `scripts/backup.sh` — `pg_dump` with retention, meant to run from cron on the server. |
| Smoke tests | `smoke.py` — `python -m app.modules.p24_hardening.smoke --base-url ...`, hits a running deployment's health + every module's base route (plus an optional login check) over plain HTTP. |
| Recovery documentation | `docs/RUNBOOK.md` — what to do when the backend is down, the database needs restoring, secrets need rotating, or GA4/GTM tracking breaks. |
| Monitoring | Structured JSON logging + `/api/v1/foundation/health` already exist (P00). Point any uptime checker (UptimeRobot, healthchecks.io, etc.) at that URL — no code needed here. |

## The one place this reaches into a frozen module
`app.main.create_app()` (owned by P00, `approved_frozen`) now calls `p24_hardening.interface.install(app)` right
after `register_error_handlers(app)`. This is a single, additive line — no existing behaviour changed, no other
line touched. See CHANGELOG.md for the explicit cross-module note.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p24_hardening/interface.py` | **public interface**: `with_retry`, `install(app)` |
| `…/rate_limit.py`, `security_headers.py`, `retry.py`, `config.py` | the hardening pieces themselves |
| `…/smoke.py` | post-deploy smoke test (standalone script, no DB import) |
| `scripts/backup.sh` | Postgres backup with retention |
| `docs/RUNBOOK.md` | recovery documentation |

## Acceptance criteria
- [x] Rate limiting (per-IP, Redis-backed with in-memory fallback), off during tests.
- [x] Security headers (nosniff, frame-deny, referrer-policy, HSTS in prod).
- [x] Retry with backoff for the Claude API calls in P09/P10/P11/P14.
- [x] Smoke test script; backup script; recovery runbook.
- [x] Retries for P04 (Google Ads) / P06 (GA4/Search Console) read calls (`request_with_retry`).
- [x] User review and approval (2026-10-06).
