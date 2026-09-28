# P16 Tests

```bash
cd backend && python -m pytest app/modules/p16_approvals tests/isolation -q
```
`tests/test_p16.py`: sync collects P14 (accepted + requires approval only), P08 (batched, new negatives → new batch), P09,
P15; idempotent; auto-withdraw when the source is no longer approved (P08 never); impact levels; approve / reject (reason) /
withdraw; `APPROVE` confirmation and self-approval note for high impact; history; counts and status filter; interface
request (idempotent) → approved_changes → mark_executed; permissions; unknown account / approval.
