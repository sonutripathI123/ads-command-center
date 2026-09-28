"use client";
// P03 — client for /api/v1/websites.
import { API_BASE } from "@/shell";

export type CrawlRun = {
  id: number; status: "running" | "success" | "partial" | "failed"; started_at: string; finished_at: string | null;
  max_pages: number; pages_found: number; pages_crawled: number; source: string; errors: string[];
};
export type Website = {
  id: number; name: string; domain: string; base_url: string; primary_service: string; location: string; time_zone: string;
  ads_account_id: number | null; ads_account_label: string | null; ads_customer_id: string | null;
  ga4_property_id: string | null; gsc_site_url: string | null; notes: string; status: string; created_at: string;
  pages: number; pages_with_issues: number; last_crawl: CrawlRun | null;
};
export type WebsiteInput = {
  name: string; domain: string; primary_service: string; location: string; time_zone: string;
  ads_account_id: number | null; ga4_property_id: string | null; gsc_site_url: string | null; notes: string;
};
export type PageRow = {
  id: number; url: string; status_code: number | null; title: string; meta_description: string; h1: string;
  word_count: number; response_ms: number | null; services: string[]; locations: string[]; issues: string[];
  has_form: boolean; has_phone: boolean; cta_count: number; last_crawled_at: string | null;
};
export type LandingPage = {
  final_url: string; status: "ok" | "broken" | "not_crawled" | "other_domain"; page_id: number | null;
  title: string | null; issues: string[]; ads: number; ad_groups: string[];
};
export type Meta = { crawler_enabled: boolean; issue_labels: Record<string, string>; ads_accounts: { id: number; customer_id: string; name: string }[] };

const BASE = `${API_BASE}/api/v1/websites`;

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

export const sitesApi = {
  meta: () => call<Meta>("/meta"),
  list: () => call<Website[]>(""),
  get: (id: number) => call<Website>(`/${id}`),
  create: (w: WebsiteInput) => call<Website>("", { method: "POST", body: JSON.stringify(w) }),
  update: (id: number, w: Partial<WebsiteInput> & { status?: string }) => call<Website>(`/${id}`, { method: "PATCH", body: JSON.stringify(w) }),
  crawl: (id: number, max_pages: number) => call<CrawlRun>(`/${id}/crawl`, { method: "POST", body: JSON.stringify({ max_pages }) }),
  crawls: (id: number) => call<CrawlRun[]>(`/${id}/crawls`),
  pages: (id: number) => call<PageRow[]>(`/${id}/pages`),
  landingPages: (id: number) => call<LandingPage[]>(`/${id}/landing-pages`),
  refreshLanding: (id: number) => call<{ mapped: number }>(`/${id}/landing-pages/refresh`, { method: "POST" }),
};
