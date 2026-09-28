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
