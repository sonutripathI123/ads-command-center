# P02 — Authentication & User Access

**Status:** approved_frozen (user approved 2026-09-23)

## Purpose
Sign-in, server-side sessions, users and roles, and the permission checks every other module uses.
Execute permission (live Google Ads changes) is off for everyone by default.

## Roles → permissions (`permissions.py`)
| Role | read | recommend | approve | admin |
|---|:-:|:-:|:-:|:-:|
| viewer | ✓ | | | |
| analyst | ✓ | ✓ | | |
| approver | ✓ | ✓ | ✓ | |
| admin | ✓ | ✓ | ✓ | ✓ |

`execute` is in **no** role. It is a per-user switch (`users.execute_enabled`, default false) that can only be set with
`python -m app.modules.p02_auth.cli set-execute EMAIL on`, which asks for typed confirmation. No API can set it.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p02_auth/interface.py` | **public interface**: `CurrentUser`, `Permission`, `get_current_user`, `require_permission`, `verify_origin`, `SESSION_COOKIE` |
| `…/router.py`, `schemas.py` | `/api/v1/auth` routes and contracts |
| `…/service.py` | login/logout/session resolve, user management rules |
| `…/security.py` | scrypt password hashing, session tokens, login throttle |
| `…/permissions.py` | roles and permissions |
| `…/models.py` | `users`, `sessions` |
| `…/cli.py` | create-admin, reset-password, set-execute |
| `backend/alembic/versions/0002_p02_users_sessions.py` | migration |
| `frontend/src/modules/auth/*` | login form, account page, users admin, API client |
| `frontend/src/app/login/page.tsx`, `frontend/src/app/account/page.tsx` | routes |
| `frontend/src/proxy.ts` | redirect to /login when no session cookie (UX only) |

## Routes
| Method | Path | Access |
|---|---|---|
| POST | `/login` | public (throttled: 5 failures / 15 min per email) |
| POST | `/logout` | any |
| GET | `/me` | signed in |
| GET | `/roles` | signed in |
| GET | `/users` | admin |
| POST | `/users` | admin |
| PATCH | `/users/{id}` | admin (role, name, active; cannot remove the last admin or deactivate yourself) |

## Security
- Passwords: scrypt (n=2^14, r=8, p=1), 16-byte salt, min 12 chars. Unknown email and wrong password give the same response.
- Sessions: 32-byte random token in an HttpOnly, SameSite=Lax cookie (Secure in production); DB stores only SHA-256 of it; 12 h lifetime; deactivating a user deletes their sessions.
- CSRF: state-changing routes reject a browser `Origin` that is not in `CORS_ORIGINS`.
- Known limits: login throttle is per-process memory (P24 moves it to Redis). Google sign-in is not in this version (see DECISIONS.md).

## Acceptance criteria
- [x] Users and roles; read/recommend/approve/admin permissions; execute off by default and not grantable via API.
- [x] Secure server-side sessions; login, logout, me.
- [x] `require_permission` dependency for other modules.
- [x] Admin user management with last-admin protection.
- [x] Frontend login + account page + route guard, with no change to P01.
- [x] User review and approval (2026-09-23).
