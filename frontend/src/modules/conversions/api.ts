"use client";
// P06 — client for /api/v1/conversions.
import { API_BASE } from "@/shell";

export type SyncRun = { id: number; status: string; started_at: string; finished_at: string | null; date_from: string; date_to: string;
  counts: Record<string, number>; errors: Record<string, string> };
export type SiteRow = { id: number; name: string; domain: string; ga4_property_id: string | null; gsc_site_url: string | null;
  ads_account_id: number | null; last_run: SyncRun | null };
export type Health = { severity: "critical" | "warning" | "info"; code: string; title: string; detail: string };
export type EventRow = { event_name: string; event_count: number; key_events: number; role: string | null; suggested_role: string };
export type BookingSummary = { count: number; revenue: number; google_ads: { count: number; revenue: number };
  by_channel: { channel: string; count: number; revenue: number }[] };
export type Overview = {
  date_from: string; date_to: string; ga4_first_day: string | null;
  channels: { channel: string; sessions: number; engaged_sessions: number; users: number; key_events: number }[];
  daily: { date: string; sessions: number }[];
  totals: { sessions: number; engaged_sessions: number; users: number; key_events: number };
  events: EventRow[]; top_queries: { query: string; clicks: number; impressions: number; position: number }[];
  organic_totals: { clicks: number; impressions: number }; bookings: BookingSummary; health: Health[];
};
export type ImportResult = { created: number; updated: number; skipped: number; errors: string[]; ignored_columns: string[] };

const BASE = `${API_BASE}/api/v1/conversions`;

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

export const convApi = {
  websites: () => call<SiteRow[]>("/websites"),
  sync: (id: number, days: number) => call<SyncRun>(`/websites/${id}/sync`, { method: "POST", body: JSON.stringify({ days }) }),
  runs: (id: number) => call<SyncRun[]>(`/websites/${id}/runs`),
  overview: (id: number, days: number) => call<Overview>(`/websites/${id}/overview?days=${days}`),
  setRole: (id: number, event_name: string, role: string) =>
    call<{ event_name: string; role: string }>(`/websites/${id}/mappings`, { method: "PUT", body: JSON.stringify({ event_name, role }) }),
  importBookings: (csv: string, default_website_id: number | null) =>
    call<ImportResult>("/bookings/import", { method: "POST", body: JSON.stringify({ csv, default_website_id }) }),
};
