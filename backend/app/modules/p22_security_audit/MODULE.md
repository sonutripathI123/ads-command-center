# P22 — Security / Audit / Rollback

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
An immutable, cross-module audit trail: who did what, when, and what the before/after values were, for every
security-sensitive action other modules choose to record. Read-only from the API — there is no edit or delete
endpoint anywhere in this module.

## What P22 owns vs. what's already done elsewhere
MID §11 P22 lists secret security, permission separation, action log, before/after values, execution kill switch,
and rollback/compensation procedures. Secret handling, RBAC (`Permission`/`require_permission`) and the execution
kill switch already live in P00/P02 (see `docs/SECURITY.md`) — P22's net-new piece is the **action log** with
before/after values. Rollback/compensation for executed changes now lives in P17 (every validate/execute/rollback is written here too).

## Model
One append-only table, `audit_logs`: `module_id`, `action`, `actor` (+ `actor_role`), `entity_type`/`entity_id`,
`before`/`after` (JSON), `note`, `request_id`, `ip`, `at`. Any module calls `interface.record(...)` — typically with
`commit=False` so it lands in the caller's own transaction — right after it changes a status or record it considers
security-sensitive.

## Wired in (v1)
- P16 (`decide`, `mark_executed`) — every approve/reject/withdraw/execute decision on a proposed Google Ads change.
- P09 (`update_draft`) — every ad draft status transition (approved/rejected).
Other modules can call `interface.record` the same way; nothing requires a P22 code change to add a new caller.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p22_security_audit/interface.py` | **public interface**: `record` |
| `…/service.py`, `router.py`, `models.py` | `/api/v1/security` (admin-only, read-only) |
| `backend/alembic/versions/0019_p22_security_audit.py` | migration |
| `frontend/src/modules/security/*`, `frontend/src/app/audit-log/page.tsx` | Audit Log page (route slug matches nav.json: `audit-log`) |

## Acceptance criteria
- [x] Immutable audit log with before/after values, queryable by module/actor/action/entity/date.
- [x] Wired into P16 approval decisions and P09 ad draft review.
- [x] Rollback/compensation procedures — provided by P17 (`/executions/{id}/rollback`).
- [ ] User review and approval.
