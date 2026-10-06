# P17 — Google Ads Execution

**Status:** approved_frozen (user approved 2026-10-06)
the owner deliberately unlocks it (see "Unlocking").

## Purpose
Take a change a human already **approved in P16** and — only when explicitly asked — validate it with Google, apply it,
or undo it. It never runs by itself (no scheduler; Level-4 automation flag `ads.execution.automation.enabled` is unused).

## Supported changes (everything else says "apply it by hand")
| P16 change type | Google request | Notes |
|---|---|---|
| `add_negative_keywords` (P08) | `campaignCriteria:mutate` | Campaign-level negatives; account-level ones are applied to every non-removed campaign. Only ever reduces traffic. |
| `create_rsa` (P09) | `adGroupAds:mutate` | Always created **PAUSED**. Blocked if the draft changed after approval or isn't linked to an existing ad group. |
Not supported yet: `create_campaign` (P15 — use the Google Ads Editor export), bidding/budget/enable changes (P14 — by hand).

## Three actions (each is one explicit request; all need the per-user **execute** permission)
1. **Validate** — Google checks the exact request with `validateOnly=true` and changes nothing.
2. **Execute (LIVE)** — needs ALL of: `ADS_EXECUTION_KILL_SWITCH=false` **and** flag `ads.execution.enabled` ON,
   execute permission, approval still `approved`, the typed word `EXECUTE`, and a successful **validate of the
   identical plan** (hash-matched) within 24 h. One atomic request (`partialFailure=false`, max 500 operations).
3. **Rollback (LIVE)** — same live guards + typed `ROLLBACK`; removes exactly the resources an execution created.

`google.send()` is the single choke point: for a live call it re-checks kill switch + flag *right before the HTTP call*,
so no caller can reach Google while locked (tested: zero requests leave the process).
Every action is stored in `executions` (plan, Google response, resource names, who) and written to the P22 audit log;
a successful execute also marks the P16 request `executed`.

## No duplicate live changes
Before talking to Google, `execute` **claims** the approval (a unique partial index allows one pending/executed/unknown execute
row per approval). Consequences: a double click, two tabs, or a retry after a crash can't send it twice. If Google *rejects*
the request the claim is released (`failed`, safe to fix and retry). If we get **no answer** (timeout/network) the status is
`unknown` and the change is never re-sent automatically — check Google Ads by hand first. Rollback is claimed the same way
(`rolling_back`) and only removes resource names that belong to the same customer. Single-tenant app: the execute
permission is global (not per account).

## Unlocking (operator only, on the server — there is no API or button for it)
1. `execute` permission for a user: `python -m app.modules.p02_auth.cli set-execute EMAIL on`
2. Flag: `python -m app.modules.p17_ads_execution.cli enable --reason "..."` (asks you to type `ENABLE LIVE EXECUTION`)
3. Environment: `ADS_EXECUTION_KILL_SWITCH=false` and restart. Re-lock any time by setting it back to `true`.
`python -m app.modules.p17_ads_execution.cli status` shows the current state. Not verified against a live account in this
build — always **validate first**; Google's answer is the final word on whether a request is acceptable.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p17_ads_execution/interface.py` | **public interface**: `execution_status`, `recent_executions` |
| `…/plans.py` (pure) | approved change → exact Google request(s); plan hash; rollback plan |
| `…/google.py` | the only mutate HTTP calls in the project |
| `…/service.py`, `router.py`, `models.py`, `cli.py` | `/api/v1/execution`, `executions` table, operator CLI |
| `backend/alembic/versions/0020_p17_ads_execution.py` | migration |
| `frontend/src/modules/execution/*`, `frontend/src/app/execution/page.tsx` | Execution page (`/execution`, not in the sidebar) |

## Acceptance criteria
- [x] Executes only P16-approved changes; validate-first; typed confirmation; kill switch + flag + permission; audit; rollback.
- [x] Locked by default; proven by tests with a fake Google (no real call is ever made by the test suite).
- [ ] Verified against the live Google Ads account (needs the owner to unlock and run validate on a real approved change).
- [ ] `create_campaign` execution; campaign-level bid/budget changes.
- [x] User review and approval (2026-10-06).
