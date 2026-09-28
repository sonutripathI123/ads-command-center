"""P09 — public interface (for P15 campaign builder, P20 experiments).

    from app.modules.p09_ad_creative.interface import check_rsa, approved_drafts, write_rsa, get_draft
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p09_ad_creative import service
from app.modules.p09_ad_creative.checks import check_ad

__all__ = ["check_rsa", "approved_drafts", "write_rsa", "get_draft"]


def check_rsa(headlines: list[str], descriptions: list[str], paths: list[str], *, keywords: list[str], locations: list[str],
              approved_claims: list[str], competitors: list[str]) -> list[dict]:
    return [f.__dict__ for f in check_ad(headlines, descriptions, paths, keywords=keywords, locations=locations,
                                         approved_claims=approved_claims, competitors=competitors)]


def approved_drafts(db: DbSession, account_id: int) -> list[dict]:
    return [service.draft_dict(db, d) for d in service.list_drafts(db, account_id, "approved")]


def write_rsa(db: DbSession, account_id: int, *, ad_group_name: str, campaign_name: str, final_url: str,
              keywords: list[str], usps: list[str], use_ai: bool, by: str) -> dict:
    """Create a checked RSA draft (Claude if live, else template). Raises P09 errors (e.g. ai_failed)."""
    d = service.create_draft(db, account_id, ad_group_name=ad_group_name, campaign_name=campaign_name, ad_group_google_id=None,
                             final_url=final_url, kw=keywords, usps=usps, use_ai=use_ai, by=by)
    return service.draft_dict(db, d)


def get_draft(db: DbSession, draft_id: int) -> dict | None:
    from app.modules.p09_ad_creative.models import AdDraft

    d = db.get(AdDraft, draft_id)
    return service.draft_dict(db, d) if d else None
