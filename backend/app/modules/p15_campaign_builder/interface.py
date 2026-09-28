"""P15 — public interface (for P16 approvals, P17 execution, P20 experiments).

    from app.modules.p15_campaign_builder.interface import get_campaign_draft, approved_campaign_drafts
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p15_campaign_builder import service
from app.modules.p15_campaign_builder.models import CampaignDraft

__all__ = ["get_campaign_draft", "approved_campaign_drafts"]


def get_campaign_draft(db: DbSession, draft_id: int) -> dict | None:
    d = db.get(CampaignDraft, draft_id)
    return service.draft_dict(db, d) if d else None


def approved_campaign_drafts(db: DbSession, account_id: int) -> list[dict]:
    return [service.draft_dict(db, d) for d in service.list_drafts(db, account_id) if d.status == "approved"]
