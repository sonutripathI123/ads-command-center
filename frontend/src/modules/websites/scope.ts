"use client";
// P03 — feeds the P01 scope selector with real websites and connected ads accounts.
import type { ScopeData } from "@/shell";
import { sitesApi } from "./api";

export async function loadScope(): Promise<ScopeData> {
  try {
    const [sites, meta] = await Promise.all([sitesApi.list(), sitesApi.meta()]);
    return {
      websites: sites.map((s) => ({ id: String(s.id), name: s.name, domain: s.domain, service: s.primary_service,
                                    location: s.location, adsAccountId: s.ads_account_id === null ? null : String(s.ads_account_id) })),
      adsAccounts: meta.ads_accounts.map((a) => ({ id: String(a.id), name: a.name, customerId: a.customer_id })),
    };
  } catch {
    return { websites: [], adsAccounts: [] }; // signed out / backend down → empty selector
  }
}
