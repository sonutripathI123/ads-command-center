"use client";
// P05 — client for /api/v1/ads-sync (read-only data + "sync now").
import { API_BASE } from "@/shell";

export type Metrics = {
  impressions: number; clicks: number; cost: number; conversions: number; conversions_value: number;
  ctr: number | null; avg_cpc: number | null; conv_rate: number | null; cost_per_conversion: number | null;
};
export type SyncRun = {
  id: number; account_id: number; status: "running" | "success" | "partial" | "failed";
  started_at: string; finished_at: string | null; date_from: string; date_to: string;
  counts: Record<string, number>; errors: Record<string, string>;
};
export type SyncAccount = {
  id: number; customer_id: string; descriptive_name: string; currency_code: string | null; time_zone: string | null;
  last_run: SyncRun | null;
};
export type Summary = { date_from: string; date_to: string; totals: Metrics; daily: (Metrics & { date: string })[] };
export type CampaignRow = Metrics & {
  google_id: string; name: string; status: string | null; channel_type: string | null;
  bidding_strategy_type: string | null; budget: number | null;
};
export type AdGroupRow = Metrics & { google_id: string; name: string; status: string | null; campaign_google_id: string; campaign_name: string;
  campaign_status: string | null; effective_status: string };
export type KeywordRow = Metrics & {
  key: string; text: string; match_type: string | null; status: string | null; quality_score: number | null;
  campaign_name: string; ad_group_name: string; campaign_google_id: string;
};
export type SearchTermRow = Metrics & {
  key: string; search_term: string; status: string | null; matched_keyword: string | null; matched_match_type: string | null;
  campaign_name: string; ad_group_name: string; first_seen: string | null;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const BASE = `${API_BASE}/api/v1/ads-sync`;

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init, credentials: "include", headers: { "content-type": "application/json", ...(init.headers ?? {}) },
  });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, body?.error?.message ?? `HTTP ${r.status}`);
  return body as T;
}

const qs = (p: Record<string, string | number | undefined | null>) =>
  "?" + Object.entries(p).filter(([, v]) => v !== undefined && v !== null && v !== "").map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&");

export const syncApi = {
  accounts: () => call<SyncAccount[]>("/accounts"),
  sync: (accountId: number, days?: number) =>
    call<SyncRun>(`/accounts/${accountId}/sync`, { method: "POST", body: JSON.stringify(days ? { days } : {}) }),
  runs: (accountId: number) => call<SyncRun[]>(`/accounts/${accountId}/runs`),
  summary: (a: number, days: number) => call<Summary>(`/accounts/${a}/summary${qs({ days })}`),
  campaigns: (a: number, days: number, include_removed?: boolean) =>
    call<CampaignRow[]>(`/accounts/${a}/campaigns${qs({ days, include_removed: include_removed ? "true" : undefined })}`),
  adGroups: (a: number, days: number, campaign_id?: string, include_removed?: boolean) =>
    call<AdGroupRow[]>(`/accounts/${a}/ad-groups${qs({ days, campaign_id, include_removed: include_removed ? "true" : undefined })}`),
  keywords: (a: number, days: number, campaign_id?: string) => call<KeywordRow[]>(`/accounts/${a}/keywords${qs({ days, campaign_id })}`),
  searchTerms: (a: number, days: number, q?: string) => call<SearchTermRow[]>(`/accounts/${a}/search-terms${qs({ days, q, limit: 2000 })}`),
};
