# P21 Tests

```bash
cd backend && python -m pytest app/modules/p21_business_rules tests/isolation -q
```
`tests/test_rules.py`: normalisation, chauffeur defaults, default when unsaved, versioning + no-op saves,
restore, account scope override, viewer read-only, validation.
