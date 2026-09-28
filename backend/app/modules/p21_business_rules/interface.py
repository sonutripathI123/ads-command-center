"""P21 — public interface.

    from app.modules.p21_business_rules.interface import Rules, get_rules
    rules = get_rules(db, account_id)   # effective rules (global + account override)
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p21_business_rules.rules import Rules
from app.modules.p21_business_rules.service import effective

__all__ = ["Rules", "get_rules"]


def get_rules(db: DbSession, account_id: int | None = None) -> Rules:
    return effective(db, account_id)
