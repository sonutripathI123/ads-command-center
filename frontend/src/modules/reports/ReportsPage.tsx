"use client";
// P19 — reports: generate account/website reports, keep snapshots, export CSV or print to PDF.
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Opt = { id: number; name: string };
type Options = { accounts: Opt[]; websites: Opt[]; periods: string[] };
type Run = { id: number; scope: string; scope_id: number; period: string; date_from: string; date_to: string; title: string;
  period_label: string; created_by: string | null; created_at: string };

const BASE = `${API_BASE}/api/v1/reports`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const input = "rounded-md border border-line bg-surface px-2 py-1 text-sm";
const btn = "rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2";
const PERIOD_LABEL: Record<string, string> = { daily: "Daily (yesterday)", weekly: "Weekly (last 7 days)", monthly: "Monthly (last full month)", custom: "Custom dates" };

export function ReportsPage() {
  const router = useRouter();
  const [opts, setOpts] = useState<Options | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [f, setF] = useState({ scope: "account", scope_id: 0, period: "weekly", date_from: "", date_to: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const loadRuns = useCallback(async () => {
    const r = await call<Run[]>("/runs");
    setRuns(r);
    setSel((s) => s ?? r[0]?.id ?? null);
  }, []);

  useEffect(() => {
    call<Options>("/options").then((o) => { setOpts(o); setF((x) => ({ ...x, scope_id: o.accounts[0]?.id ?? o.websites[0]?.id ?? 0, scope: o.accounts.length ? "account" : "website" })); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/reports"); else setMsg({ ok: false, text: (e as Error).message }); });
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial load
    loadRuns().catch(() => undefined);
  }, [router, loadRuns]);

  async function generate() {
    setBusy(true); setMsg(null);
    try {
      const body = { scope: f.scope, scope_id: f.scope_id, period: f.period, ...(f.period === "custom" ? { date_from: f.date_from || null, date_to: f.date_to || null } : {}) };
      const r = await call<Run>("/runs", { method: "POST", body: JSON.stringify(body) });
      setMsg({ ok: true, text: `“${r.title}” ready.` });
      await loadRuns(); setSel(r.id);
    } catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(false); }
  }

  const choices = f.scope === "account" ? opts?.accounts ?? [] : opts?.websites ?? [];
  const current = runs.find((r) => r.id === sel);
  return (
    <>
      <PageHeader title="Reports" moduleId="P19" />
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      <section className="mb-4 rounded-lg border border-line bg-surface p-4">
        <h2 className="mb-2 font-semibold">New report</h2>
        <div className="flex flex-wrap items-end gap-2 text-sm">
          <label className="text-xs text-muted">Report on<br />
            <select className={input} value={f.scope} onChange={(e) => { const scope = e.target.value; setF({ ...f, scope, scope_id: (scope === "account" ? opts?.accounts : opts?.websites)?.[0]?.id ?? 0 }); }}>
              <option value="account">Google Ads account</option><option value="website">Website</option>
            </select>
          </label>
          <label className="text-xs text-muted">Which<br />
            <select className={input} value={f.scope_id} onChange={(e) => setF({ ...f, scope_id: Number(e.target.value) })}>
              {choices.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <label className="text-xs text-muted">Period<br />
            <select className={input} value={f.period} onChange={(e) => setF({ ...f, period: e.target.value })}>
              {(opts?.periods ?? []).map((p) => <option key={p} value={p}>{PERIOD_LABEL[p] ?? p}</option>)}
            </select>
          </label>
          {f.period === "custom" && <>
            <label className="text-xs text-muted">From<br /><input type="date" className={input} value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} /></label>
            <label className="text-xs text-muted">To<br /><input type="date" className={input} value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} /></label>
          </>}
          <button onClick={generate} disabled={busy || !f.scope_id} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">{busy ? "Building…" : "Generate report"}</button>
        </div>
        <p className="mt-2 text-xs text-muted">Sync Google Ads and GA4 first for up-to-date numbers. Each report is saved as a snapshot, so it won&apos;t change later.</p>
      </section>
      {!runs.length && <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">No reports yet.</p>}
      {runs.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <ol className="grid content-start gap-1">
            {runs.map((r) => (
              <li key={r.id}>
                <button onClick={() => setSel(r.id)} aria-current={r.id === sel}
                  className={`w-full rounded-md border px-3 py-2 text-left text-sm ${r.id === sel ? "border-accent bg-accent-soft" : "border-line bg-surface hover:bg-surface-2"}`}>
                  <span className="block truncate font-medium">{r.title}</span>
                  <span className="text-xs text-muted">{r.period_label} · {new Date(r.created_at).toLocaleString("en-AU")}</span>
                </button>
              </li>
            ))}
          </ol>
          {current && (
            <section className="grid gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="flex-1 font-semibold">{current.title}</h2>
                <a className={btn} href={`${BASE}/runs/${current.id}/csv`}>Download CSV</a>
                <a className={btn} href={`${BASE}/runs/${current.id}/html`} target="_blank" rel="noreferrer">Open printable / Save as PDF</a>
              </div>
              <iframe title={current.title} src={`${BASE}/runs/${current.id}/html`} className="h-[70vh] w-full rounded-lg border border-line bg-white" />
            </section>
          )}
        </div>
      )}
    </>
  );
}
