# P04 Changelog

## 2026-09-23 — initial build
- OAuth connect (state HMAC + nonce cookie), Fernet-encrypted refresh tokens, userinfo email.
- Discovery via listAccessibleCustomers + GAQL customer/customer_client; add/disable accounts; check; disconnect+revoke.
- Read-only REST adapter on Google Ads API v26 (SELECT-only search).
- Interface for P05: `active_accounts`, `open_read_session`.
- Frontend `/ads-accounts` page.
- Dependency: `cryptography` added to backend/requirements.txt (approved P00 file change).
- Status: `review`.
## 2026-09-28 — env import CLI
- `cli.py`: `check-env PREFIX` (verify refresh token, developer token, account) and `import-env PREFIX`
  (store encrypted connection + add account) — for accounts whose tokens already exist.
- Default Google Ads API version v26 -> v25 (v26 returned 'Method not found' with a real token; v22-v25 work).
- Status: `approved_frozen` (user approved 2026-09-28).

## 2026-10-06 — retries on read calls (owner-approved change to a frozen module)
- Token refresh, list-accessible-customers and GAQL search now go through P24's `request_with_retry`: timeouts, connection errors
  and HTTP 429/5xx are retried up to 3 times with backoff; the last response is returned unchanged, so error handling is as before.
  The one-time authorization-code exchange, revoke and userinfo calls are deliberately NOT retried. `depends_on` gained P24.
  Still read-only: no mutate call exists here. Tests: `tests/test_retries.py`.
