"""P09 — public interface (for P15 campaign builder, P20 experiments).

    from app.modules.p09_ad_creative.interface import check_rsa, approved_drafts
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p09_ad_creative import service
from app.modules.p09_ad_creative.checks import check_ad

__all__ = ["check_rsa", "approved_drafts"]


def check_rsa(headlines: list[str], descriptions: list[str], paths: list[str], *, keywords: list[str], locations: list[str],
              approved_claims: list[str], competitors: list[str]) -> list[dict]:
    return [f.__dict__ for f in check_ad(headlines, descriptions, paths, keywords=keywords, locations=locations,
                                         approved_claims=approved_claims, competitors=competitors)]


def approved_drafts(db: DbSession, account_id: int) -> list[dict]:
    return [service.draft_dict(db, d) for d in service.list_drafts(db, account_id, "approved")]
