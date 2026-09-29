# P22 Changelog

## 2026-09-29 — initial build
- `audit_logs`: immutable, append-only table (module_id, action, actor, entity, before/after JSON, note).
  `interface.record(...)` is the only write path; no edit/delete endpoint anywhere.
- Read-only admin API: `GET /audit-logs` (filters: module, actor, action, entity_type/id, since/until), `GET /audit-logs/{id}`,
  `GET /audit-logs/facets`.
- Wired into P16 (`decide`, `mark_executed`) and P09 (`update_draft` status transitions); registry updated so P09
  depends on P22. Migration `0018_p19` → `0019_p22`. Status: `review`.
- Rollback/compensation procedures deferred: nothing executes against Google Ads yet (P17 still planned), so there
  is nothing to compensate for.
