# P23 — Testing & QA

**Status:** approved_frozen (user approved 2026-10-12)

## Purpose
MID §11 P23 lists: unit tests, integration tests, API mocks, fixture-based AI tests, approval tests, isolation tests,
regression tests. Module tests live beside each module and `tests/isolation` already guards the architecture; this module
adds the shared harness and the product-wide audits that no single module owns.

## What's here
| Piece | File | What it gives you |
|---|---|---|
| API mocks | `fakes.py` | `FakeClaude` replays recorded AI answers, records prompts, simulates rate limit / refusal / cut-off / network failure. `FakeAdsAPI` returns the rows you give it and raises `MutationAttempted` on any Google Ads mutation. |
| Recorded AI fixtures | `fixtures/*.json` | Known-good AI answers (`ad_copy_ok` obeys every Google limit) used instead of calling Claude. |
| Route auditor | `audit.py` | Walks every `/api/v1` route and reports findings: anonymous callers must get 401; a READ-only user must get 403 on every write. |
| QA command line | `cli.py` | `python -m app.modules.p23_testing_qa.cli` (anonymous audit, safe anywhere) and `--roles` (also the READ-only audit, development database only). |
| Product-wide tests | `tests/test_qa.py` | Harness self-tests, the two audits, approval/execute permission checks, and the regression that live execution stays locked (guarded flags off by default; the kill switch beats any override). |

## Boundaries
- Imports other modules only through `p02_auth.interface` (current-user dependency, `Permission`).
- No tables, no routes, no UI, no feature flags. It never calls Google Ads or Claude.
- Isolation, registry and migration checks stay in `backend/tests/isolation/` (owned by P00).

## Acceptance criteria
- [x] API mocks for Claude and Google Ads (mutations refused).
- [x] Recorded fixture for the AI ad writer, validated against Google's limits.
- [x] Route audit: no protected route answers an anonymous caller; a READ-only user cannot write anywhere.
- [x] Approval and execution permission tests (analyst cannot approve; approver without `execute` cannot run live changes).
- [x] Regression: execution flags off by default and beaten by the kill switch.
- [x] User review and approval (2026-10-12).
