# P12 — Budget / Bid / Geo / Device / Time Intelligence

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
Show *where* and *when* the Google Ads money works or is wasted: by device, day of week, time of day, location, and per
campaign budget / ad-rank. Advice only — it reads Google Ads (GAQL SELECT through P04) and changes nothing anywhere.

## What is pulled (read-only, on demand — "Run analysis")
| Table | Source (GAQL) |
|---|---|
| Device, day of week, hour | `campaign` with `segments.device / day_of_week / hour`, summed across campaigns |
| Location | `user_location_view` with `segments.geo_target_most_specific_location`, names via `geo_target_constant` (suburb / postcode / city) |
| Budget & ad rank | `campaign` with daily budget, bidding strategy, search impression share, share lost to budget, share lost to rank |
Day-parts (late night / morning / afternoon / evening) group the 24 hours so each has enough clicks to say anything.
The snapshot is stored (`segment_runs`, last 10 per account) and the findings in `segment_findings`.

## Honesty rules (`analysis.py`, pure)
- "No conversions" is only called out when the segment would **expect ≥ 3 conversions at the account average** (otherwise
  zero is plausible luck); the expected number is shown in the evidence. Cost-per-conversion calls need ≥ 3 conversions.
- Every finding states confidence (`low`/`medium`), its numbers, and a proposed action. Small samples are never "certain".
- Nothing is concluded when the account has no conversions at all — it says to fix tracking first.
- Places inside Victoria are never recommended for cutting on thin evidence; places outside Australia and places you
  listed as not served (P21) are flagged as facts (spend + clicks), not statistics.
- Budget: raise only if the campaign converts at an acceptable cost; otherwise says "don't yet". Flags losing mostly on ad rank
  (quality/bids, not budget), spend without conversions, and "Maximize clicks" bidding.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p12_budget_bid/interface.py` | **public interface**: `segment_findings` (for P19) |
| `…/gaql.py` (reads), `analysis.py` (pure), `service.py`, `router.py`, `models.py` | `/api/v1/budget-bid` |
| `backend/alembic/versions/0021_p12_budget_bid.py` | migration |
| `frontend/src/modules/budget-bid/*`, `frontend/src/app/budget-bid/page.tsx` | page `/budget-bid` (linked from Monitoring; not a sidebar section) |

## Acceptance criteria
- [x] Device / day / time / location / budget analysis from real Google Ads data; findings with evidence, confidence and action.
- [x] Read-only (test asserts every query is a SELECT); no change to Google Ads.
- [ ] Applying bid adjustments / schedules / exclusions from the app (P17 doesn't support those change types yet).
- [ ] Ad-group / keyword level and audience segments. [ ] User review and approval.
