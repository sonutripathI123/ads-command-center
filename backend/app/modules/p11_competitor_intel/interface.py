"""P11 — public interface (for P14 recommendations, P15 campaign builder, P19 reports).

    from app.modules.p11_competitor_intel.interface import competitor_summary
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p11_competitor_intel import service

__all__ = ["competitor_summary"]


def competitor_summary(db: DbSession, account_id: int) -> dict:
    """Competitor names, service/location content gaps and the latest interpretation's opportunities."""
    return service.summary(db, account_id)
