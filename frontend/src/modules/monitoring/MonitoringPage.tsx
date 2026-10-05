"use client";
// P18 — monitoring: one alert per problem, auto-resolved when it clears; manual or scheduled checks.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Alert = { id: number; code: string; severity: "critical" | "warning" | "info"; title: string; detail: string; action: string;
  evidence: [string, string][]; link: string | null; status: string; occurrences: number; first_seen_at: string; last_seen_at: string;
  acknowledged_by: string | null; resolved_at: string | null; resolved_by: string | null };
type Run = { id: number; trigger: string; status: string; signals: number; opened: number; resolved: number; error: string | null;
  run_by: string | null; started_at: string };
type Account = { id: number; customer_id: string; name: string; open: Record<string, number> };
type Meta = { scheduled_enabled: boolean; accounts: Account[] };

const BASE = `${API_BASE}/api/v1/monitoring`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const SEV = { critical: "bg-danger/15 text-danger", warning: "bg-warn/15 text-warn", info: "bg-surface-2 text-muted" } as const;
const btn = "rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2 disabled:opacity-50";
const when = (s: string) => new Date(s).toLocaleString("en-AU");

export function MonitoringPage() {
  const router = useRouter();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [accId, setAccId] = useState<number | null>(null);
  const [tab, setTab] = useState<"open" | "resolved">("open");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    call<Meta>("/accounts").then((m) => { setMeta(m); if (m.accounts[0]) setAccId(m.accounts[0].id); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/monitoring"); else setMsg({ ok: false, text: (e as Error).message }); });
  }, [router]);

  const load = useCallback(async () => {
    if (!accId) return;
    const r = await call<{ alerts: Alert[]; runs: Run[] }>(`/accounts/${accId}${tab === "resolved" ? "?status=resolved" : ""}`);
    setAlerts(r.alerts); setRuns(r.runs);
  }, [accId, tab]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on selection change
    load().catch((e) => setMsg({ ok: false, text: (e as Error).message }));
  }, [load]);

  async function act(label: string, fn: () => Promise<unknown>, ok?: string) {
    setBusy(label); setMsg(null);
    try { await fn(); if (ok) setMsg({ ok: true, text: ok }); await load(); }
    catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(null); }
  }
  const runNow = () => act("run", async () => {
    const r = await call<Run>(`/accounts/${accId}/run`, { method: "POST" });
    setMsg({ ok: true, text: `Checked: ${r.signals} issue(s) found · ${r.opened} new · ${r.resolved} cleared.` });
  });
  const setStatus = (a: Alert, status: string) => act(`s${a.id}`, () => call(`/alerts/${a.id}/status`, { method: "POST", body: JSON.stringify({ status }) }));

  return (
    <>
      <PageHeader title="Monitoring & Alerts" moduleId="P18">
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/budget-bid" className="text-xs text-accent underline">Budget &amp; bid insights →</Link>
          {meta && meta.accounts.length > 1 && (
            <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => setAccId(Number(e.target.value))}>
              {meta.accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
            </select>
          )}
          <button onClick={runNow} disabled={!accId || !!busy} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
            {busy === "run" ? "Checking…" : "Run checks now"}</button>
        </div>
      </PageHeader>
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      <p className="mb-4 text-sm text-muted">
        Compares the last 7 days with the usual week (28 days before): spend spikes or stops, conversion drops, CPC and CTR changes, new search terms
        eating the budget, and broken tracking. One alert per problem; it clears itself when the problem goes away.
        {meta && !meta.scheduled_enabled && <> Automatic daily checks are off — they need the flag <code>monitoring.scheduled.enabled</code> and a Windows scheduled task.</>}
      </p>
      <div role="tablist" className="mb-3 flex w-fit overflow-hidden rounded-md border border-line">
        {(["open", "resolved"] as const).map((k) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`px-3 py-1 text-sm ${tab === k ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"}`}>{k === "open" ? "Open" : "Resolved"}</button>
        ))}
      </div>
      {accId && !alerts.length && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">
          {tab === "open" ? (runs.length ? "All clear — no open alerts." : "No checks run yet. Click “Run checks now”.") : "No resolved alerts yet."}
        </p>
      )}
      <ol className="mb-6 grid gap-2">
        {alerts.map((a) => (
          <li key={a.id} className="rounded-lg border border-line bg-surface p-3 text-sm">
            <div className="flex flex-wrap items-start gap-2">
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${SEV[a.severity]}`}>{a.severity}</span>
              <span className="flex-1 font-medium">{a.title}</span>
              {a.status === "acknowledged" && <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] text-muted">acknowledged by {a.acknowledged_by}</span>}
            </div>
            {a.detail && <p className="mt-1 text-xs text-muted">{a.detail}</p>}
            {a.evidence.length > 0 && (
              <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 text-xs">
                {a.evidence.map(([k, v], i) => <Fragment key={i}><dt className="text-muted">{k}</dt><dd>{v}</dd></Fragment>)}
              </dl>
            )}
            <p className="mt-1"><span className="text-xs text-muted">Do: </span>{a.action}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
              <span>First seen {when(a.first_seen_at)} · seen {a.occurrences}×{a.resolved_at && <> · resolved {when(a.resolved_at)} by {a.resolved_by}</>}</span>
              {a.link && <Link href={a.link} className="text-accent underline">Open →</Link>}
              {a.status === "open" && <button className={btn} disabled={!!busy} onClick={() => setStatus(a, "acknowledged")}>Acknowledge</button>}
              {a.status !== "resolved" && <button className={btn} disabled={!!busy} onClick={() => setStatus(a, "resolved")}>Mark resolved</button>}
            </div>
          </li>
        ))}
      </ol>
      {runs.length > 0 && (
        <section className="rounded-lg border border-line bg-surface p-4">
          <h2 className="mb-2 font-semibold">Recent checks</h2>
          <ul className="grid gap-1 text-xs">
            {runs.map((r) => (
              <li key={r.id} className={r.status === "failed" ? "text-danger" : "text-muted"}>
                {when(r.started_at)} · {r.trigger} · {r.status}{r.status === "success" ? ` · ${r.signals} issue(s), ${r.opened} new, ${r.resolved} cleared` : r.error ? ` · ${r.error}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
