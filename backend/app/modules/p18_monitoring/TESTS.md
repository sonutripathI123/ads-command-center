# P18 Tests

```bash
cd backend && python -m pytest app/modules/p18_monitoring tests/isolation -q
```
`tests/test_p18.py`: windows; quiet week → no alerts; spend spike (critical), CPC up/down, spend stopped, conversion
drop, no recent data, CTR drop, search-term shift (and below threshold), critical-only tracking; API: open/dedupe
(tracking deduped across websites)/occurrences/auto-resolve, acknowledge keeps one alert, manual resolve, bad status,
account badge counts, interface; scheduled run respects the flag; failed run recorded; permissions.
