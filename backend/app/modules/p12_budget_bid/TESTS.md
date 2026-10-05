# P12 Tests

```bash
cd backend && python -m pytest app/modules/p12_budget_bid tests/isolation -q
```
`tests/test_p12.py` — no network (fake read session, canned GAQL rows): day-parts sum to the total; the "no conversions" call
needs >= 3 expected conversions (flagged vs. not flagged); expensive/efficient segments; confidence + action on every finding;
no conversions at all -> says so instead of blaming segments; outside-country and not-served locations; home-region waste
softened; budget findings (limited / unproven / rank-limited / spend without conversions / maximize-clicks; paused skipped);
the pull aggregates and orders correctly and **only ever sends SELECT queries**; run stores a snapshot, a failed read is
recorded and reported, only the latest 10 runs are kept; API: read-only users can view but not run (403), unknown account 404,
run works with the recommend permission, bad `days` -> 422.
