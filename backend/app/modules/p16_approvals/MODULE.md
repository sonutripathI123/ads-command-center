# P16 — Approval Center

**Status:** review (awaiting user acceptance, MID §22)

## Purpose
One queue for every proposed Google Ads change, with before/after, evidence, risk and impact, and a recorded human
decision. P17 (execution, not built; kill switch on) may only ever execute items that are **approved** here.

## Where requests come from ("Sync queue")
| Source | What is queued | Change type | Impact |
|---|---|---|---|
| P14 recommendations | accepted recommendations that need approval | bidding_change / enable_campaigns / keyword_change / ad_change / … | high for bidding & enabling campaigns |
| P08 negatives | accepted negative keywords not yet in a request (one batch) | add_negative_keywords | standard |
| P09 ad copy | approved RSA drafts | create_rsa | standard |
| P15 campaign builder | approved campaign drafts (created **paused**) | create_campaign | high |
| any module (interface) | e.g. P20 "start experiment" | start_experiment … | per type |

Sync is idempotent. If a P09/P14/P15 source is no longer approved/accepted, its open request is withdrawn automatically.
P08 batches are never auto-withdrawn.

## Decision rules
- Approve / reject needs the **approve** permission; withdraw needs recommend.
- High-impact changes need the confirmation phrase `APPROVE`; approving your own high-impact request needs a note.
- Rejecting needs a reason. Every step is written to `approval_events` (history shown on each card).
- Approving does **not** change Google Ads — execution is P17's job and is disabled.

## Files
| File | Role |
|---|---|
| `backend/app/modules/p16_approvals/interface.py` | **public interface**: `request_approval`, `get_approval`, `approved_changes`, `mark_executed` |
| `…/service.py`, `router.py`, `models.py` | queue sync, decisions, history; `/api/v1/approvals` |
| `backend/alembic/versions/0013_p16_approvals.py` | migration |
| `frontend/src/modules/approvals/*`, `frontend/src/app/approvals/page.tsx` | Approval Center page |

## Acceptance criteria
- [x] Pending / approved / rejected / withdrawn / executed lists with before/after, evidence, risk, impact.
- [x] Approve / reject / withdraw with notes; confirmation for high-impact; full history.
- [x] Sources: P08, P09, P14, P15 + interface for other modules; P17 reads `approved_changes` only.
- [ ] User review and approval.
