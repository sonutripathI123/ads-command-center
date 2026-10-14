# P09 Tests

```bash
cd backend && python -m pytest app/modules/p09_ad_creative tests/isolation -q
```
`tests/test_p09.py`: every text rule, approved-claim exemption, ad-level rules + strength, template copy passes all hard
rules, strict schema; API: existing-ad analysis, ad-group options, template draft, live draft via fake Claude (brief
contents, findings), AI failure → 502, edit → re-check → approve blocked by errors → approve → CSV, permissions.

Smart ad copy (`tests/test_p09.py`, bottom): split_ads per goal, avoid_lines dedupe/cap, honesty text in the brief,
repeat counting + notes, history reaches Claude, second draft avoids the first, `learn=false`, history-source failure
does not block drafting, invalid goal → 422.

Campaign review (`tests/test_p09.py`, bottom): account-wide benchmark, suggestions for structure and performance, honest
output without data, campaign filter on the analysis endpoint (suggestions + benchmark present).
