"use client";
// P08 — client for /api/v1/keywords.
import { API_BASE } from "@/shell";

export type Negative = {
  id: number; text: string; match_type: "PHRASE" | "EXACT"; campaign_google_id: string | null; campaign_name: string | null;
  level: "campaign" | "account"; source: string; confidence: number; reason: string; cost: number; clicks: number;
  impressions: number; conversions: number; term_count: number; examples: string[];
  status: "proposed" | "accepted" | "rejected" | "stale"; reviewed_by: string | null;
};
export type AnalyzeResult = {
  date_from: string; date_to: string; search_terms: number; intents: Record<string, number>;
  negative_candidates: number; high_confidence_waste: number; expansion_candidates: number;
};
export type InsightRow = Record<string, unknown> & { reason: string; cost: number; clicks: number; conversions: number };
export type Insights = Record<"wasters" | "winners" | "low_quality_score" | "idle" | "duplicates" | "expansion_candidates", InsightRow[]>
  & { enabled_campaigns: number };

const BASE = `${API_BASE}/api/v1/keywords`;

async function call<T>(path: string, init: RequestInit = {}, as: "json" | "text" = "json"): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  if (!r.ok) {
    const body = await r.json().catch(() => null);
    throw new Error(body?.error?.message ?? `HTTP ${r.status}`);
  }
  return (as === "text" ? await r.text() : await r.json()) as T;
}

export const kwApi = {
  analyze: (a: number, days: number) => call<AnalyzeResult>(`/accounts/${a}/analyze?days=${days}`, { method: "POST" }),
  negatives: (a: number, status: string, minConfidence: number) =>
    call<Negative[]>(`/accounts/${a}/negatives?min_confidence=${minConfidence}${status ? `&status=${status}` : ""}`),
  review: (a: number, ids: number[], status: "proposed" | "accepted" | "rejected") =>
    call<{ updated: number }>(`/accounts/${a}/negatives/review`, { method: "POST", body: JSON.stringify({ ids, status }) }),
  exportText: (a: number) => call<string>(`/accounts/${a}/negatives/export?fmt=text`, {}, "text"),
  csvUrl: (a: number) => `${BASE}/accounts/${a}/negatives/export?fmt=csv`,
  insights: (a: number, days: number) => call<Insights>(`/accounts/${a}/insights?days=${days}`),
};

export const asGoogleAds = (n: Pick<Negative, "text" | "match_type">) => (n.match_type === "PHRASE" ? `"${n.text}"` : `[${n.text}]`);
