"""P12 — public interface (for P19 reports).

    from app.modules.p12_budget_bid.interface import segment_findings
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p12_budget_bid import service

__all__ = ["segment_findings"]


def segment_findings(db: DbSession, account_id: int) -> list[dict]:
    """Findings of the latest successful analysis (warnings first); empty if none was run yet."""
    snap = service.latest(db, account_id)
    return snap["findings"] if snap else []
