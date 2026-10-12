# P23 Tests

```bash
cd backend && python -m pytest app/modules/p23_testing_qa tests/isolation -q
python -m app.modules.p23_testing_qa.cli            # anonymous route audit (safe anywhere)
python -m app.modules.p23_testing_qa.cli --roles    # plus READ-only write audit (development database only)
```

`tests/test_qa.py`:
- Harness: recorded ad-copy fixture obeys Google limits; every fixture is valid JSON; `FakeClaude` replays in order and
  records prompts; its four failure modes; `FakeAdsAPI` reads but refuses every mutation.
- Audits on the real app: route inventory is complete (100+ routes, all five HTTP verbs); every protected route answers
  anonymous callers with 401; a READ-only user gets 403 on every write route.
- Permissions: an analyst cannot approve or touch execution; an approver without the `execute` permission cannot run or
  roll back live changes.
- Regression: `ads.execution.enabled` and `ads.execution.automation.enabled` are off by default, health reports the kill
  switch, and the kill switch beats any database override (and only lifting it lets the flags take effect).
