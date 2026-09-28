# P07 Tests

```bash
cd backend && python -m pytest app/modules/p07_ppc_audit tests/isolation -q
```
`tests/test_audit.py`: full synthetic account → all expected issues, severity ordering, contract fields, healthy account = 100,
target CPA + no website, huge ad group warning; API run/latest/accounts, dismissal persistence across runs, one failing
data source, permissions/validation. Other modules are replaced via their interfaces.
