"""P19 — public interface (for a future scheduled email/Slack sender).

    from app.modules.p19_reports.interface import generate_report
"""
from datetime import date

from sqlalchemy.orm import Session as DbSession

from app.modules.p19_reports import service

__all__ = ["generate_report"]


def generate_report(db: DbSession, *, scope: str, scope_id: int, period: str, by: str,
                    d1: date | None = None, d2: date | None = None) -> dict:
    """Generate and store a report; returns its snapshot (title, period, content)."""
    return service.run_dict(service.generate(db, scope=scope, scope_id=scope_id, period=period, d1=d1, d2=d2, by=by))
