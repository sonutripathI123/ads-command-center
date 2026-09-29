# P22 Tests

```bash
cd backend && python -m pytest app/modules/p22_security_audit tests/isolation -q
```
`tests/test_p22.py`: `record` serializes before/after and defaults; `query` filters by module/actor/entity/limit;
`facets`; API list/get/facets under the admin permission, 404 for an unknown id, 403 without admin.

Also covered indirectly: `app/modules/p16_approvals` and `app/modules/p09_ad_creative` test suites exercise the
retrofit calls (`decide`, `mark_executed`, `update_draft`) that write into `audit_logs`.
