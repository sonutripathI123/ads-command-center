"""P17 — public interface (for P18 change-impact monitoring and P19 reports).

    from app.modules.p17_ads_execution.interface import execution_status, recent_executions
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p17_ads_execution import service

__all__ = ["execution_status", "recent_executions"]


def execution_status(db: DbSession) -> dict:
    """{kill_switch, flag_enabled, live_execution_allowed, ...} — whether live execution is possible right now."""
    return service.status(db)


def recent_executions(db: DbSession, account_id: int, limit: int = 20) -> list[dict]:
    return service.history(db, account_id, limit)
