"use client";
// P02 — client for /api/v1/auth. Cookies are HttpOnly; the browser sends them with credentials: "include".
import { API_BASE } from "@/shell";

export type Me = { id: number; email: string; name: string; role: string; permissions: string[] };
export type UserRow = {
  id: number; email: string; name: string; role: string;
  execute_enabled: boolean; is_active: boolean; created_at: string; last_login_at: string | null;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${API_BASE}/api/v1/auth${path}`, {
    ...init,
    credentials: "include",
    headers: { "content-type": "application/json", ...(init.headers ?? {}) },
  });
  if (r.status === 204) return undefined as T;
  const body = await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, body?.error?.message ?? `HTTP ${r.status}`);
  return body as T;
}

export const authApi = {
  login: (email: string, password: string) => call<Me>("/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => call<void>("/logout", { method: "POST" }),
  me: () => call<Me>("/me"),
  roles: () => call<{ roles: Record<string, string[]> }>("/roles"),
  users: () => call<UserRow[]>("/users"),
  createUser: (u: { email: string; name: string; role: string; password: string }) =>
    call<UserRow>("/users", { method: "POST", body: JSON.stringify(u) }),
  updateUser: (id: number, patch: { role?: string; is_active?: boolean }) =>
    call<UserRow>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
};
