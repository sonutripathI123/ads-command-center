"""P06 — public interface (for P07 audit, P12 budget, P13 funnel/attribution, P18 monitoring, P19 reports).

    from app.modules.p06_analytics.interface import website_overview, bookings_summary, tracking_health
"""
from datetime import date

from sqlalchemy.orm import Session as DbSession

from app.modules.p06_analytics import service

__all__ = ["website_overview", "bookings_summary", "tracking_health"]


def website_overview(db: DbSession, website_id: int, d1: date, d2: date) -> dict:
    """GA4 traffic by channel + events (with lead/booking roles) + Search Console queries + bookings + health."""
    return service.overview(db, service.website(db, website_id), d1, d2)


def bookings_summary(db: DbSession, d1: date, d2: date, website_id: int | None = None) -> dict:
    """Confirmed bookings (cancelled excluded): count, revenue, Google Ads share, by channel."""
    return service.bookings_summary(db, d1, d2, website_id)


def tracking_health(db: DbSession, website_id: int, d1: date, d2: date) -> list[dict]:
    return website_overview(db, website_id, d1, d2)["health"]
