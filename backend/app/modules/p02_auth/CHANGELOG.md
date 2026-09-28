# P02 Changelog

## 2026-09-23 — initial build
- Users + sessions (migration `0002_p02`), fixed roles (viewer/analyst/approver/admin), per-user execute switch (CLI only).
- `/api/v1/auth` login/logout/me/roles/users; scrypt hashing, hashed session tokens, login throttle, Origin check.
- Public interface `require_permission` for other modules.
- Frontend: `/login`, `/account` (users admin), `proxy.ts` route guard.
- Registry: tables reduced from users/roles/user_roles/sessions to users/sessions (roles live in code).
- Status: `review`.

## 2026-09-23 — approval + follow-ups
- CLI: `--visible` option for create-admin/reset-password (hidden input failed to match in the user's terminal).
- `UserMenu` (name → /account, Sign out) shown in the shell top bar; /login shown without shell chrome.
- Status: `approved_frozen` (user approved 2026-09-23).

## 2026-09-28 — fix (approved change request)
- `proxy.ts`: no longer redirects `/login` → `/` when a session cookie exists. A leftover cookie from an
  expired/revoked session made the login page unreachable. Only file changed: `frontend/src/proxy.ts`.
