// P05 — public interface of the Ads data frontend module (P07/P08/P12/P19 may reuse these).
export { CampaignsPage, AdGroupsPage, KeywordsPage, SearchTermsPage } from "./pages";
export { AdsDataFrame, type FrameCtx } from "./AdsDataFrame";
export { DataTable, type Column } from "./DataTable";
export { SpendChart } from "./SpendChart";
export { syncApi, type Metrics, type CampaignRow, type KeywordRow, type SearchTermRow } from "./api";
export { money, num, pct, title } from "./format";
