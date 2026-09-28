"""P14 — public interface (for P16 approvals, P17 execution, P19 reports).

    from app.modules.p14_recommendations.interface import open_recommendations, get_recommendation
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p14_recommendations import service
from app.modules.p14_recommendations.models import Recommendation

__all__ = ["open_recommendations", "get_recommendation"]


def open_recommendations(db: DbSession, account_id: int) -> list[dict]:
    """Proposed + accepted recommendations, highest priority first (MID §18 dicts)."""
    return [service.rec_dict(r) for r in service.list_recs(db, account_id) if r.status in ("proposed", "accepted")]


def get_recommendation(db: DbSession, rec_id: int) -> dict | None:
    r = db.get(Recommendation, rec_id)
    return service.rec_dict(r) if r else None
