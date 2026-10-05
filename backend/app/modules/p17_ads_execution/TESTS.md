# P17 Tests

```bash
cd backend && python -m pytest app/modules/p17_ads_execution tests/isolation -q
```
`tests/test_p17.py` — **never touches the network**: Google is a fake `httpx.MockTransport`; P04/P05/P09/P16 are replaced
through their interfaces. Covers: request building (campaign/account-level negatives, dedupe, 500-op cap, RSA paused +
shape, draft-changed/unlinked blocks, plan hash); `validateOnly` flag on every body; **live send blocked by the kill
switch with zero HTTP requests**; validate records + audits without marking P16 executed; execute blocked while locked,
needs confirmation and a hash-matching validation; full validate → execute → rollback; Google rejection recorded and
P16 untouched; only approved + supported changes run; API: read-only users can look but not act (403), execute
permission alone still can't go live (409) and only validate-only traffic is ever sent.
