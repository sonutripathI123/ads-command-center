# P08 Tests

```bash
cd backend && python -m pytest app/modules/p08_keyword_intel tests/isolation -q
```
- `tests/test_analysis.py` (pure): intent table, whole-word matching, phrase negatives + evidence, conversion and
  service-word downgrades, exact negatives, relevant terms protected, thresholds, already-excluded, coverage
  de-dup, pattern words, insight buckets, paused-campaign handling, target CPA.
- `tests/test_api.py`: analyze summary, confidence ordering + filter, review persistence across re-analysis,
  text/CSV export, stale handling, validation, permissions, classifications, insights, unknown account.
  P05/P21/P02 are replaced via their public interfaces.
