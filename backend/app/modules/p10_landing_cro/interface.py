"""P10 — public interface (for P14 recommendations, P19 reports).

    from app.modules.p10_landing_cro.interface import landing_scores
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p10_landing_cro import service

__all__ = ["landing_scores"]


def landing_scores(db: DbSession, account_id: int) -> list[dict]:
    """Latest check per ad landing URL: url, score (0–100), critical finding count, checked_at."""
    return service.latest_scores(db, account_id)
