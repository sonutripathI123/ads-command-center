# P09 Changelog

## 2026-09-28 — initial build
- RSA checks + strength; existing-ad analysis; Claude/template writer; drafts with review + Editor CSV export.
- Ads & Assets page (Existing ads / Write new ads / Drafts with live character counts and preview).
- Migration `0011_p09`. Registry: depends_on P02, P05, P21 (P14 removed — not used).
- First live draft (Corporate Cars, "Corporate Chauffeur Melbourne"): 15 headlines / 4 descriptions, 0 findings.
- Status: `review`.
- Interface: `write_rsa`, `get_draft` (for P15 Campaign Builder).

## 2026-10-06 — approved and frozen by the owner
- Status `review` -> `approved_frozen`. Further changes need an explicit request that targets this module (docs/CHANGE_PROTOCOL.md).

## 2026-10-12 — Smart ad copy (owner request: "bana do dono")
Explicit change request targeting this frozen module: one click writes an ad from the account's own history.
- New `context.py` (pure functions): picks the best / weakest responsive search ads for the chosen **goal**
  (`conversions`, `clicks`, `cpa`), the search terms that converted, and the copy written or run recently; builds extra
  briefing text. Small samples are flagged as hints and no number may be quoted in an ad.
- `create_draft(..., goal, learn)`: when `learn` is on, the 90-day ads and search terms (P05 interface) and the last 30
  days of drafts feed the Claude brief ("do NOT reuse these lines"). After generation, lines identical to avoided lines
  are counted and reported in the draft notes. Template mode cannot learn and says so. A failing history source never
  blocks drafting.
- API: `POST /accounts/{id}/drafts` accepts `goal` (default `conversions`) and `learn` (default `true`).
  `interface.write_rsa` gained optional `goal`/`learn` (default off), so P15 behaves exactly as before.
- Frontend: "Goal of this ad" dropdown and a "Smart copy" checkbox on Write new ads; draft notes keep line breaks.
- No migration, no new tables, no new imports of other modules beyond `search_terms` from P05's existing interface.
- Tests: 9 new (ranking per goal, avoid-list, honesty text, repeat count, history sent to Claude, second draft avoids the
  first, learn off, source failure, bad goal rejected).

## 2026-10-12 — keywords are cleaned before writing (owner request)
- `clean_keywords`: `[exact]`, `"phrase"` and `+broad` decoration is stripped from the keyword box, blanks and duplicates dropped.
  Match types belong to keywords in a campaign, never to ad copy, and the decoration could leak into a headline. 1 new test.
