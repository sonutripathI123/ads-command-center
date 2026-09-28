# P09 Tests

```bash
cd backend && python -m pytest app/modules/p09_ad_creative tests/isolation -q
```
`tests/test_p09.py`: every text rule, approved-claim exemption, ad-level rules + strength, template copy passes all hard
rules, strict schema; API: existing-ad analysis, ad-group options, template draft, live draft via fake Claude (brief
contents, findings), AI failure → 502, edit → re-check → approve blocked by errors → approve → CSV, permissions.
