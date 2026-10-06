# P20 — Experiments

**Status:** approved_frozen (user approved 2026-10-06)

## Purpose
Test one change at a time and measure it honestly from synced Google Ads data (P05), with the caveats written next to
the result. Running an experiment needs a P16 approval. Nothing is changed in Google Ads by this module.

## Experiment types
- **A/B** — two campaigns / ad groups / ads over the same dates (control vs variant).
- **Before/after** — one entity, a baseline period vs the test period (after a change was made).

## Lifecycle
draft (editable) → submit → **pending_approval** (P16 "start_experiment") → start (only once approved) → **running** →
analyze (any time; stored while running) → complete (conclusion required). Rejected/withdrawn approval → back to draft.
Cancel any time before completion.

## Analysis (`stats.py`)
- CTR and conversion rate: two-proportion z-test, significant at p < 0.05.
- Avg. CPC and cost/conversion: lift only (directional, no test).
- Verdict on the primary metric: variant_better / control_better / no_significant_difference / directional_… /
  insufficient_data (below the minimum clicks per side).
- Limitations always listed: sample size, unfinished period, P06 critical tracking issues (conversion metrics
  unreliable), seasonality for before/after, unequal period lengths, no clicks.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p20_experiments/interface.py` | **public interface**: `experiments_summary` (for P19) |
| `…/stats.py` | pure comparison maths |
| `…/service.py`, `router.py`, `models.py` | lifecycle + analysis; `/api/v1/experiments` |
| `backend/alembic/versions/0014_p20_experiments.py` | migration |
| `frontend/src/modules/experiments/*`, `frontend/src/app/experiments/page.tsx` | Experiments page |

## Acceptance criteria
- [x] Hypothesis, change, control/variant, primary metric, periods, minimum sample.
- [x] Approval through P16 before running; results with significance and limitations; conclusion.
- [x] User review and approval (2026-10-06).
