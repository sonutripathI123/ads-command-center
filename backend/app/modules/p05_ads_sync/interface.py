"""P05 — public interface for analysis modules (P07 audit, P08 keywords, P12 budget, P13 funnel, P19 reports).

All functions return plain dicts with metrics already derived (cost in account currency, ctr, avg_cpc,
conv_rate, cost_per_conversion). Dates are inclusive. `list_accounts` returns the synced (active) accounts,
so analysis modules don't need to depend on P04 directly.
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p04_ads_connection.interface import AccountRef, active_accounts
from app.modules.p05_ads_sync.service import ad_groups, ads, campaigns, keywords, search_terms, summary

__all__ = ["AccountRef", "list_accounts", "summary", "campaigns", "ad_groups", "keywords", "search_terms", "ads"]


def list_accounts(db: DbSession) -> list[AccountRef]:
    return active_accounts(db)
