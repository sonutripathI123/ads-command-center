"use client";
// One-click "Sync now" for the whole dashboard: Google Ads + GA4 + Search Console (read-only syncs), then a
// monitoring check, then the page reloads so every screen shows the fresh numbers.
import { useState } from "react";
import { API_BASE } from "@/shell";

type Run = { id: number; status: "running" | "success" | "partial" | "failed"; errors?: Record<string, string> };
type Job = { label: string; startPath: string; runsPath: string; runId: number | null; done: boolean; status: Run["status"] | "error"; note: string };

class HttpError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${API_BASE}/api/v1/${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw new HttpError(r.status, body?.error?.message ?? `HTTP ${r.status}`);
  return body as T;
}

const sleep = (ms: number) => new Promise((res) => setTimeout(res, ms));
const MAX_WAIT_MS = 5 * 60 * 1000;

async function runJob(job: Job, update: () => void): Promise<void> {
  try {
    try {
      job.runId = (await call<Run>(job.startPath, { method: "POST", body: "{}" })).id;
    } catch (e) {
      if (e instanceof HttpError && e.status === 403) throw e;
      // a sync may already be running (e.g. started from another page) — fall through and wait for the latest run
    }
    const t0 = Date.now();
    while (Date.now() - t0 < MAX_WAIT_MS) {
      await sleep(2000);
      const runs = await call<Run[]>(job.runsPath);
      const r = job.runId ? runs.find((x) => x.id === job.runId) : runs[0];
      if (r && r.status !== "running") {
        job.done = true; job.status = r.status;
        job.note = r.status === "success" ? "done" : Object.values(r.errors ?? {})[0] ?? r.status;
        return;
      }
      if (!r && !job.runId) { job.done = true; job.status = "error"; job.note = "could not start"; return; }
    }
    job.done = true; job.status = "error"; job.note = "timed out";
  } catch (e) {
    job.done = true; job.status = "error";
    job.note = e instanceof HttpError && e.status === 403 ? "needs analyst permission" : (e as Error).message;
  } finally {
    update();
  }
}

export function SyncAllButton() {
  const [busy, setBusy] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  async function syncAll() {
    setBusy(true); setMsg(null);
    try {
      const [accounts, sites] = await Promise.all([
        call<{ id: number; customer_id: string }[]>("ads-sync/accounts"),
        call<{ id: number; name: string }[]>("conversions/websites"),
      ]);
      const list: Job[] = [
        ...accounts.map((a): Job => ({ label: `Google Ads ${a.customer_id}`, startPath: `ads-sync/accounts/${a.id}/sync`,
          runsPath: `ads-sync/accounts/${a.id}/runs`, runId: null, done: false, status: "running", note: "" })),
        ...sites.map((s): Job => ({ label: `GA4 + Search Console (${s.name})`, startPath: `conversions/websites/${s.id}/sync`,
          runsPath: `conversions/websites/${s.id}/runs`, runId: null, done: false, status: "running", note: "" })),
      ];
      if (!list.length) { setMsg("Nothing to sync yet — connect an ads account or add a website first."); return; }
      const refresh = () => setJobs([...list]);
      refresh();
      await Promise.all(list.map((j) => runJob(j, refresh)));
      // fresh numbers → refresh the alerts too (read-only checks; best effort)
      await Promise.all(accounts.map((a) => call(`monitoring/accounts/${a.id}/run`, { method: "POST" }).catch(() => null)));
      const ok = list.some((j) => j.status === "success" || j.status === "partial");
      if (ok) {
        setMsg("Synced — reloading…");
        setTimeout(() => window.location.reload(), 900);
        return;
      }
      setMsg("Sync failed — see details.");
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-2 text-xs">
      {(busy || msg) && (
        <span role="status" className="max-w-[28rem] truncate text-muted" title={jobs.map((j) => `${j.label}: ${j.done ? j.note : "syncing…"}`).join("\n")}>
          {msg ?? jobs.map((j) => `${j.label.split(" (")[0]}: ${j.done ? (j.status === "success" ? "✓" : j.note) : "…"}`).join(" · ")}
        </span>
      )}
      <button onClick={syncAll} disabled={busy} className="rounded-md bg-accent px-2.5 py-1 font-medium text-white disabled:opacity-60">
        {busy ? "Syncing…" : "Sync now"}
      </button>
    </div>
  );
}
