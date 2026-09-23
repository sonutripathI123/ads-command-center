# P02 Changelog

## 2026-09-23 — initial build
- Users + sessions (migration `0002_p02`), fixed roles (viewer/analyst/approver/admin), per-user execute switch (CLI only).
- `/api/v1/auth` login/logout/me/roles/users; scrypt hashing, hashed session tokens, login throttle, Origin check.
- Public interface `require_permission` for other modules.
- Frontend: `/login`, `/account` (users admin), `proxy.ts` route guard.
- Registry: tables reduced from users/roles/user_roles/sessions to users/sessions (roles live in code).
- Status: `review`.
