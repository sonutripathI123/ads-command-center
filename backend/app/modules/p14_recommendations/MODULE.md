# P14 — AI Recommendation Engine

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
One standard recommendation store (MID §18 contract) fed by analysis modules (today: P07 audit), prioritised,
with a decision workflow, plus an **AI action plan** written by Claude from the stored evidence.

## Recommendation contract
id · module_id · website_id · ads_account_id · entity_type/id · category · severity · priority · title ·
observation · evidence[] · reasoning · proposed_action · expected_impact · confidence · risk · assumptions[] ·
requires_approval · status · decided_by · created_at · approved_at · executed_at · execution_result.
- priority = 300/200/100 (critical/warning/info) + confidence×100 − risk penalty (medium 20, high 50).
- requires_approval = true for anything changed **inside Google Ads** (account, bidding, keywords, search terms, ads);
  P16 will hold those approvals, P17 the (flagged, kill-switched) execution. Tracking / landing pages / organic are
  off-platform fixes.
- Status: proposed → accepted → done; proposed → rejected; proposed → superseded (source stopped reporting it).
  Decisions survive re-refresh.

## AI action plan (`ai.py`)
- Live only when **both** flag `ai.live_calls.enabled` and `ANTHROPIC_API_KEY` are set; otherwise a rule-based
  template plan with the same shape.
- Official `anthropic` SDK; model `claude-opus-5`, adaptive thinking, effort high, structured JSON output
  (strict schema), server-side refusal fallback to `claude-opus-4-8`; stop reasons checked; output validated with
  Pydantic; unknown recommendation ids dropped. Prompt forbids booking/revenue promises.
- Every run is stored (`ai_runs`: mode, model, tokens, output/error) with the evidence used (`ai_evidence`).

## Files
| File | Role |
|---|---|
| `backend/app/modules/p14_recommendations/interface.py` | **public interface**: `open_recommendations`, `get_recommendation` |
| `…/ai.py` | plan schema, Claude call, template plan |
| `…/service.py`, `router.py`, `models.py` | ingest, prioritise, decisions, plans; `/api/v1/recommendations` |
| `backend/alembic/versions/0010_p14_recommendations.py` | migration |
| `frontend/src/modules/recommendations/*`, `frontend/src/app/recommendations/page.tsx` | AI Recommendations page |

## Configuration
`ANTHROPIC_API_KEY` (backend/.env), optional `AI_MODEL` (default claude-opus-5);
`python -m app.shared.flags_cli set ai.live_calls.enabled on --reason "..."`. Dependency: `anthropic>=1.8`.

## Acceptance criteria
- [x] Standard schema with evidence, reasoning, confidence, risk, impact, priority, approval state; observation vs inference separated.
- [x] Decision workflow; ingestion from P07; superseding.
- [x] AI plan with traceable evidence; safe when AI is off.
- [ ] Live Claude plan tested with a real key (needs ANTHROPIC_API_KEY + flag).
- [ ] User review and approval.
