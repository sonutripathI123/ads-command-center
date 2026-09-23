"use client";
// P04 — client for /api/v1/ads-connection.
import { API_BASE } from "@/shell";

export type Connection = {
  id: number; google_email: string | null; status: string;
  last_checked_at: string | null; last_error: string | null; created_at: string;
};
export type Account = {
  id: number; customer_id: string; descriptive_name: string; currency_code: string | null; time_zone: string | null;
  is_manager: boolean; is_test_account: boolean; login_customer_id: string | null; connection_id: number;
  status: string; added_at: string;
};
export type Discovered = {
  customer_id: string; descriptive_name: string; currency_code: string | null; time_zone: string | null;
  is_manager: boolean; is_test_account: boolean; status: string | null; login_customer_id: string | null;
  already_added: boolean;
};
export type Status = {
  oauth_client_configured: boolean; developer_token_configured: boolean; api_version: string; redirect_uri: string;
  connections: Connection[]; accounts: Account[];
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const BASE = `${API_BASE}/api/v1/ads-connection`;

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init, credentials: "include", headers: { "content-type": "application/json", ...(init.headers ?? {}) },
  });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, body?.error?.message ?? `HTTP ${r.status}`);
  return body as T;
}

export const adsApi = {
  connectUrl: `${BASE}/oauth/start`,
  status: () => call<Status>("/status"),
  check: (id: number) => call<{ connection: Connection; accessible_customer_ids: string[] }>(`/connections/${id}/check`, { method: "POST" }),
  disconnect: (id: number) => call<Connection>(`/connections/${id}/disconnect`, { method: "POST" }),
  discover: (id: number) => call<Discovered[]>(`/connections/${id}/discover`),
  addAccount: (connection_id: number, customer_id: string, login_customer_id: string | null) =>
    call<Account>("/accounts", { method: "POST", body: JSON.stringify({ connection_id, customer_id, login_customer_id }) }),
  setStatus: (id: number, status: "active" | "disabled") =>
    call<Account>(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
};

export const formatCid = (cid: string) => cid.replace(/^(\d{3})(\d{3})(\d{4})$/, "$1-$2-$3");
