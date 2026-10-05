# P17 Changelog

## 2026-10-05 — initial build (ships locked)
- Validate / execute / rollback for P16-approved `add_negative_keywords` and `create_rsa` (PAUSED). Migration `0020_p17`.
- Guards: kill switch + flag + per-user execute permission + typed confirmation + hash-matched validation (24 h) + atomic
  request; re-checked inside `google.send()` right before the HTTP call. Audit via P22; P16 marked `executed` on success.
- Operator CLI `python -m app.modules.p17_ads_execution.cli enable|disable|status` (the only way to flip the flag).
- No Google Ads call is made by this build or its tests; the account is untouched. Status `review`.

- Independent security review applied: atomic claim before any live send (no duplicate changes after crash/timeout/double
  click), `unknown` outcome state for network errors, atomic rollback claim + same-customer check, numeric Google ids only,
  RSA ad group bound to what was approved, CLI `enable` needs a real terminal and ignores `--by`.

**CROSS-MODULE CHANGES** (declared per docs/CHANGE_PROTOCOL.md):
- P04 (`approved_frozen`) `interface.py`: added `ApiCredentials` + `open_api_credentials()` — hands P17 the short-lived
  authenticated headers and versioned base URL. P04 itself still contains no mutate call. Additive; nothing else changed.
- `docs/modules.json`: P17 `planned` → `review`; `depends_on` gained `P09` (reads the approved ad draft's ad group).
- Not done: `create_campaign` execution (P15), bid/budget/enable changes (P14), P24 retries around Google calls
  (mutations are deliberately NOT auto-retried).
