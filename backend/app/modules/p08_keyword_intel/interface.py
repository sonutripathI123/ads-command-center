"""P08 — public interface (for P07 audit, P14 recommendations, P15 campaign builder).

    from app.modules.p08_keyword_intel.interface import accepted_negatives, classify_terms
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p08_keyword_intel.analysis import Classifier
from app.modules.p08_keyword_intel.service import list_negatives
from app.modules.p21_business_rules.interface import get_rules

__all__ = ["accepted_negatives", "classify_terms"]


def accepted_negatives(db: DbSession, account_id: int) -> list[dict]:
    return list_negatives(db, account_id, status="accepted", min_confidence=0)


def classify_terms(db: DbSession, account_id: int | None, terms: list[str]) -> dict[str, tuple[str, str, list[str]]]:
    clf = Classifier(get_rules(db, account_id))
    return {t: clf.classify(t) for t in terms}
