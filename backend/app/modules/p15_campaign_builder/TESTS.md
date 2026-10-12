# P15 Tests

```bash
cd backend && python -m pytest app/modules/p15_campaign_builder tests/isolation -q
```
`tests/test_p15.py`: theme detection (incl. plurals), clustering + negatives + de-dup + theme filter, rental-with-driver kept /
jobs negated, landing-page choice (theme URL, broken pages skipped, generic → homepage), settings vs tracking health;
API build, every edit op, write ads via P09 (USPs + campaign passed), approval gating (ads missing / not approved, tracking
not blocking), locked when approved, Editor CSV, permissions, validation, account options with keyword counts.

`test_set_match_type`: change to BROAD, invalid match type -> 422, unknown keyword -> 422.
