"""P20 — public interface (for P19 reports).

    from app.modules.p20_experiments.interface import experiments_summary
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p20_experiments import service

__all__ = ["experiments_summary"]


def experiments_summary(db: DbSession, account_id: int) -> list[dict]:
    """Every experiment with its latest stored results and conclusion (newest first)."""
    return [service.experiment_dict(db, e) for e in service.list_experiments(db, account_id)]
