# P04 — Google Ads Connection

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Connect a Google login to the dashboard (OAuth), discover the Google Ads accounts it can read (incl. accounts
under a manager/MCC), add chosen accounts, and check connection health. **Read-only**: no mutate calls exist here.

## Flow
1. Admin clicks **Connect Google Ads** → `GET /oauth/start` → Google consent (scopes: adwords, openid, email; offline).
2. Google → `GET /oauth/callback` → state verified (HMAC + browser nonce cookie + same admin, 10 min) →
   refresh token encrypted (Fernet) into `connections` → redirect to `/ads-accounts?connected=<id>`.
3. **Find accounts** → `listAccessibleCustomers` + GAQL `customer` / `customer_client` (manager children).
4. **Add** → verified with a GAQL read, stored in `ads_accounts` (with `login_customer_id` when reached through a manager).

## Files
| File | Role |
|---|---|
| `backend/app/modules/p04_ads_connection/interface.py` | **public interface** for P05/P17: `active_accounts(db)`, `open_read_session(db, account_id, http)` → `ReadSession.search(gaql)` |
| `…/adapters/google_ads.py` | OAuth + Google Ads REST **read-only** adapter (SELECT-only search) |
| `…/service.py` | OAuth state, connect, discover, add/disable, check, disconnect |
| `…/router.py`, `schemas.py` | `/api/v1/ads-connection` routes |
| `…/models.py` | `connections`, `ads_accounts` |
| `…/crypto.py`, `config.py` | token encryption; module settings |
| `backend/alembic/versions/0003_p04_connections_ads_accounts.py` | migration |
| `frontend/src/modules/ads-connection/*`, `frontend/src/app/ads-accounts/page.tsx` | Ads Accounts page |

## Routes
| Method | Path | Access |
|---|---|---|
| GET | `/status` | read |
| GET | `/oauth/start` | admin |
| GET | `/oauth/callback` | admin session (from Google redirect) |
| POST | `/connections/{id}/check` | admin |
| POST | `/connections/{id}/disconnect` | admin (revokes at Google, disables its accounts) |
| GET | `/connections/{id}/discover` | admin |
| POST | `/accounts` | admin |
| PATCH | `/accounts/{id}` | admin (active/disabled) |

## Configuration (`backend/.env`)
Shared: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_ADS_DEVELOPER_TOKEN`.
P04: `GOOGLE_ADS_API_VERSION` (default v26), `GOOGLE_ADS_OAUTH_REDIRECT_URI`, `FRONTEND_URL`,
`CREDENTIALS_ENCRYPTION_KEY` (required in production; dev derives one from `APP_SECRET_KEY` — changing
`APP_SECRET_KEY` in dev makes stored tokens unreadable → reconnect).

## Acceptance criteria
- [x] OAuth connect with CSRF-safe state; refresh token encrypted at rest, never returned by the API.
- [x] Manager/customer account discovery and selection.
- [x] Read-only health check with clear errors (deleted client, revoked grant, missing developer token, no permission).
- [x] Disconnect revokes the grant.
- [x] `ReadSession` interface for P05.
- [ ] Real connection tested with the user's Google account (needs a new OAuth client).
- [ ] User review and approval.
