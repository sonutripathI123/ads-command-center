"""P18 — public interface (for P01 overview badges, P19 reports).

    from app.modules.p18_monitoring.interface import open_alerts
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p18_monitoring import service

__all__ = ["open_alerts"]


def open_alerts(db: DbSession, account_id: int) -> list[dict]:
    """Open + acknowledged alerts, most severe first."""
    return [service.alert_dict(a) for a in service.alerts(db, account_id)]
