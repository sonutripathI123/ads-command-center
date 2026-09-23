"use client";
// P01 — read-only client for P00 foundation endpoints. No other module's API is called from the shell.
import { useEffect, useState } from "react";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Health = { status: string; database: boolean; env: string; execution_kill_switch: boolean };
export type ModuleInfo = { id: string; name: string; slug: string; status: string; depends_on: string[]; api_prefix: string | null };
export type Flag = { key: string; module_id: string; enabled: boolean; source: string; description: string };

type Result<T> = { data: T | null; error: string | null; loading: boolean };

export function useFoundation<T>(path: "health" | "modules" | "flags"): Result<T> {
  const [state, setState] = useState<Result<T>>({ data: null, error: null, loading: true });
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/v1/foundation/${path}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return (await r.json()) as T;
      })
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((e: Error) => !cancelled && setState({ data: null, error: e.message, loading: false }));
    return () => {
      cancelled = true;
    };
  }, [path]);
  return state;
}
