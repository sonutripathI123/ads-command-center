"""P07 — public interface (for P14 recommendations, P18 monitoring, P19 reports).

    from app.modules.p07_ppc_audit.interface import latest_audit
"""
import json

from sqlalchemy.orm import Session as DbSession

from app.modules.p07_ppc_audit import service

__all__ = ["latest_audit"]


def latest_audit(db: DbSession, account_id: int) -> dict | None:
    """Latest run with its open issues (MID §18-shaped dicts), or None if never audited."""
    run, issues = service.latest(db, account_id)
    if run is None:
        return None
    return {"score": run.score, "created_at": run.created_at, "days": run.days, "counts": json.loads(run.counts),
            "issues": [{"code": i.code, "category": i.category, "severity": i.severity, "title": i.title,
                        "observation": i.observation, "evidence": json.loads(i.evidence), "reasoning": i.reasoning,
                        "proposed_action": i.action, "expected_impact": i.impact, "confidence": i.confidence, "risk": i.risk,
                        "entity_type": i.entity_type, "entity_id": i.entity_id} for i in issues if i.status == "open"]}
