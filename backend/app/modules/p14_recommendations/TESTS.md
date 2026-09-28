# P14 Tests

```bash
cd backend && python -m pytest app/modules/p14_recommendations tests/isolation -q
```
`tests/test_p14.py`: ingest + priority order + requires_approval, idempotent refresh + superseding, audit required,
status workflow (incl. illegal transitions, decisions survive refresh), template plan with AI off, live plan via a fake
Claude call (prompt contents, unknown ids dropped, evidence rows, token counts), live error recorded, strict schema +
no-promise rule, permissions. Claude is never called for real in tests.
