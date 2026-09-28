"use client";
// P05 — shared frame for the data pages: account picker, date range, sync status + "Sync now".
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { PageHeader } from "@/shell";
import { ApiError, syncApi, type SyncAccount, type SyncRun } from "./api";
import { ago } from "./format";

export type FrameCtx = { accountId: number; days: number; currency: string; refreshKey: number };
const RANGES = [7, 30, 90];
const STORE = "p05.frame";

function load(): { accountId?: number; days?: number } {
  try {
    return JSON.parse(localStorage.getItem(STORE) ?? "{}");
  } catch {
    return {};
  }
}

export function AdsDataFrame({ title, children }: { title: string; children: (ctx: FrameCtx) => ReactNode }) {
  const router = useRouter();
  const [accounts, setAccounts] = useState<SyncAccount[] | null>(null);
  const [accountId, setAccountId] = useState<number | null>(null);
  const [days, setDays] = useState(30);
  const [run, setRun] = useState<SyncRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    syncApi.accounts().then((list) => {
      setAccounts(list);
      const saved = load();
      const pick = list.find((a) => a.id === saved.accountId) ?? list[0];
      if (pick) {
        setAccountId(pick.id);
        setRun(pick.last_run);
      }
      if (saved.days && RANGES.includes(saved.days)) setDays(saved.days);
    }).catch((e: ApiError) => {
      if (e.status === 401) router.replace("/login");
      else setError(e.message);
    });
    return () => {
      if (poll.current) clearInterval(poll.current);
    };
  }, [router]);

  useEffect(() => {
    try {
      localStorage.setItem(STORE, JSON.stringify({ accountId, days }));
    } catch {
      /* ignore */
    }
  }, [accountId, days]);

  const watch = useCallback((accId: number) => {
    if (poll.current) clearInterval(poll.current);
    poll.current = setInterval(async () => {
      const [latest] = await syncApi.runs(accId).catch(() => [null]);
      if (!latest) return;
      setRun(latest);
      if (latest.status !== "running" && poll.current) {
        clearInterval(poll.current);
        poll.current = null;
        setRefreshKey((k) => k + 1);
      }
    }, 2000);
  }, []);

  async function syncNow() {
    if (!accountId) return;
    setError(null);
    try {
      const r = await syncApi.sync(accountId);
      setRun(r);
      watch(accountId);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const account = accounts?.find((a) => a.id === accountId);
  const running = run?.status === "running";
  const btn = "rounded-md border border-line px-2.5 py-1 text-sm";

  return (
    <>
      <PageHeader title={title} moduleId="P05">
        <div className="flex flex-wrap items-center gap-2">
          {accounts && accounts.length > 1 && (
            <select className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accountId ?? ""}
              onChange={(e) => { const a = accounts.find((x) => x.id === Number(e.target.value)); setAccountId(a?.id ?? null); setRun(a?.last_run ?? null); }}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.descriptive_name || a.customer_id}</option>)}
            </select>
          )}
          <div role="group" aria-label="Date range" className="flex overflow-hidden rounded-md border border-line">
            {RANGES.map((d) => (
              <button key={d} onClick={() => setDays(d)} aria-pressed={days === d}
                className={`px-2.5 py-1 text-sm ${days === d ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"}`}>
                {d}d
              </button>
            ))}
          </div>
          <button className={btn} onClick={syncNow} disabled={!accountId || running}>{running ? "Syncing…" : "Sync now"}</button>
        </div>
      </PageHeader>

      {account && (
        <p className="-mt-3 mb-4 text-xs text-muted">
          {account.descriptive_name || "Account"} {account.customer_id.replace(/^(\d{3})(\d{3})(\d{4})$/, "$1-$2-$3")} ·
          {" "}last sync {run ? `${ago(run.finished_at ?? run.started_at)} (${run.status})` : "never"}
          {run && Object.keys(run.errors).length > 0 && (
            <span className="text-danger"> · {Object.entries(run.errors).map(([k, v]) => `${k}: ${v}`).join("; ")}</span>
          )}
        </p>
      )}
      {error && <p className="mb-4 text-sm text-danger" role="alert">{error}</p>}
      {accounts && accounts.length === 0 && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">
          No Google Ads account connected. Add one on the <Link className="text-accent underline" href="/ads-accounts">Ads Accounts</Link> page.
        </p>
      )}
      {account && !run && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">
          No data yet. Click <b>Sync now</b> to import the last 90 days.
        </p>
      )}
      {account && run && children({ accountId: account.id, days, currency: account.currency_code ?? "AUD", refreshKey })}
    </>
  );
}
