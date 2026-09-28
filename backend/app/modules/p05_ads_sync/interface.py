"""P05 — public interface for analysis modules (P07 audit, P08 keywords, P12 budget, P13 funnel, P19 reports).

All functions return plain dicts with metrics already derived (cost in account currency, ctr, avg_cpc,
conv_rate, cost_per_conversion). Dates are inclusive.
"""
from app.modules.p05_ads_sync.service import ad_groups, ads, campaigns, keywords, search_terms, summary

__all__ = ["summary", "campaigns", "ad_groups", "keywords", "search_terms", "ads"]
