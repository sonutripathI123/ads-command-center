# P20 Tests

```bash
cd backend && python -m pytest app/modules/p20_experiments tests/isolation -q
```
`tests/test_p20.py`: z-test values and edge cases; verdicts (variant/control better, no difference, insufficient data,
directional); meta + entity options; validation (same control/variant, unknown refs, bad type/metric/dates, baseline
overlap, min clicks); A/B lifecycle (edit → submit → P16 request → blocked until approved → running → analyze stored →
complete with conclusion); before/after preview not stored, seasonality caveat, rejection returns to draft, cancel,
future period; permissions; interface summary.
