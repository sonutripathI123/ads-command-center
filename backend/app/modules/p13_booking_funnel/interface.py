"""P13 — public interface (for P18 monitoring, P19 reports).

    from app.modules.p13_booking_funnel.interface import website_funnel
"""
from datetime import date

from sqlalchemy.orm import Session as DbSession

from app.modules.p13_booking_funnel import service

__all__ = ["website_funnel"]


def website_funnel(db: DbSession, website_id: int, d1: date | None = None, d2: date | None = None) -> dict:
    """Stages (impressions → clicks → paid visits → leads (est.) → bookings → revenue) vs the previous period,
    bottlenecks, Google-Ads-reported campaign figures and booking quality by channel."""
    return service.website_funnel(db, website_id, d1, d2)
