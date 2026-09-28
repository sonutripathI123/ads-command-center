"use client";
// P07 — account audit: score, prioritised issues with evidence, dismiss/restore, history.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Run = { id: number; score: number; days: number; counts: Record<string, number>; errors: string[]; triggered_by: string | null; created_at: string };
type Issue = {
  id: number; code: string; category: string; severity: "critical" | "warning" | "info"; title: string; observation: string;
  evidence: [string, string][]; reasoning: string; proposed_action: string; expected_impact: string; confidence: number;
  risk: string; link: string | null; status: string; dismissed_by: string | null; dismiss_note: string | null;
};
type Account = { id: number; customer_id: string; name: string; last_audit: Run | null };

const BASE = `${API_BASE}/api/v1/audit`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const CATS: Record<string, string> = {
  tracking: "Conversion tracking", account: "Account", bidding: "Bidding", keywords: "Keywords", search_terms: "Search terms",
  ads: "Ads", landing_pages: "Landing pages", organic: "Organic search",
};
const SEV = {
  critical: { label: "Critical", cls: "border-danger/40 bg-danger/5", badge: "bg-danger/15 text-danger" },
  warning: { label: "Warning", cls: "border-warn/40 bg-warn/5", badge: "bg-warn/15 text-warn" },
  info: { label: "Info", cls: "border-line bg-surface", badge: "bg-surface-2 text-muted" },
} as const;
const grade = (s: number) => (s >= 85 ? ["Good", "text-ok"] : s >= 60 ? ["Needs work", "text-warn"] : ["Poor", "text-danger"]);

export function AuditPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [accId, setAccId] = useState<number | null>(null);
  const [days, setDays] = useState(90);
  const [run, setRun] = useState<Run | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [dismissedCount, setDismissedCount] = useState(0);
  const [showDismissed, setShowDismissed] = useState(false);
  const [cat, setCat] = useState<string>("");
  const [open, setOpen] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    call<Account[]>("/accounts").then((a) => { setAccounts(a); if (a[0]) setAccId(a[0].id); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/audit"); else setMsg((e as Error).message); });
  }, [router]);

  const load = useCallback(async () => {
    if (!accId) return;
    const r = await call<{ run: Run | null; issues: Issue[]; dismissed: number }>(`/accounts/${accId}/latest?include_dismissed=${showDismissed}`);
    setRun(r.run); setIssues(r.issues); setDismissedCount(r.dismissed);
    setOpen(new Set(r.issues.filter((i) => i.severity === "critical").map((i) => i.id)));
  }, [accId, showDismissed]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on selection change
    load().catch((e) => setMsg((e as Error).message));
  }, [load]);

  async function runAudit() {
    if (!accId) return;
    setBusy(true); setMsg(null);
    try {
      await call<Run>(`/accounts/${accId}/run`, { method: "POST", body: JSON.stringify({ days }) });
      await load();
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  }

  async function setStatus(i: Issue, status: "open" | "dismissed") {
    const note = status === "dismissed" ? prompt("Why dismiss this? (optional — e.g. 'intentional')") ?? undefined : undefined;
    try {
      await call(`/issues/${i.id}/status`, { method: "POST", body: JSON.stringify({ status, note }) });
      await load();
    } catch (e) { setMsg((e as Error).message); }
  }

  const shown = issues.filter((i) => !cat || i.category === cat);
  const cats = [...new Set(issues.map((i) => i.category))];
  const toggle = (id: number) => setOpen((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const [g, gcls] = run ? grade(run.score) : ["", ""];

  return (
    <>
      <PageHeader title="Account audit" moduleId="P07">
        <div className="flex flex-wrap items-center gap-2">
          {accounts && accounts.length > 1 && (
            <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => setAccId(Number(e.target.value))}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
            </select>
          )}
          <select aria-label="Period" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[30, 60, 90, 180].map((d) => <option key={d} value={d}>last {d} days</option>)}
          </select>
          <button onClick={runAudit} disabled={!accId || busy} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
            {busy ? "Auditing…" : run ? "Run audit again" : "Run audit"}
          </button>
        </div>
      </PageHeader>
      {msg && <p className="mb-4 text-sm text-danger" role="alert">{msg}</p>}
      {accounts && !accounts.length && <p className="text-sm text-muted">Connect a Google Ads account first (<Link className="text-accent underline" href="/ads-accounts">Ads Accounts</Link>).</p>}

      {!run && accId && <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">No audit yet. Click <b>Run audit</b> — it checks tracking, bidding, keywords, search terms, ads, landing pages and organic search. Nothing is changed in Google Ads.</p>}

      {run && (
        <>
          <section className="mb-4 flex flex-wrap items-center gap-6 rounded-lg border border-line bg-surface p-4">
            <div>
              <div className="text-sm text-muted">Health score</div>
              <div className="text-4xl font-semibold tabular-nums">{run.score}<span className="text-lg text-muted">/100</span></div>
              <div className={`text-sm font-medium ${gcls}`}>{g}</div>
            </div>
            <div className="flex gap-3">
              {(["critical", "warning", "info"] as const).map((s) => (
                <div key={s} className={`rounded-md px-3 py-2 text-center ${SEV[s].badge}`}>
                  <div className="text-2xl font-semibold tabular-nums">{run.counts[s] ?? 0}</div><div className="text-xs">{SEV[s].label}</div>
                </div>
              ))}
            </div>
            <div className="ml-auto text-xs text-muted">
              Last {run.days} days · run {new Date(run.created_at).toLocaleString("en-AU")} by {run.triggered_by ?? "?"}
              {run.errors.length > 0 && <div className="text-warn">Some data unavailable: {run.errors.join("; ")}</div>}
            </div>
          </section>

          <div className="mb-3 flex flex-wrap items-center gap-2">
            <button onClick={() => setCat("")} className={`rounded-full border px-2.5 py-0.5 text-xs ${!cat ? "border-accent bg-accent-soft text-accent" : "border-line"}`}>All ({issues.length})</button>
            {cats.map((c) => (
              <button key={c} onClick={() => setCat(c)} className={`rounded-full border px-2.5 py-0.5 text-xs ${cat === c ? "border-accent bg-accent-soft text-accent" : "border-line"}`}>
                {CATS[c] ?? c} ({issues.filter((i) => i.category === c).length})
              </button>
            ))}
            {dismissedCount > 0 && (
              <label className="ml-auto flex items-center gap-1.5 text-xs text-muted">
                <input type="checkbox" checked={showDismissed} onChange={(e) => setShowDismissed(e.target.checked)} /> show {dismissedCount} dismissed
              </label>
            )}
          </div>

          <ol className="grid gap-2">
            {shown.map((i, n) => (
              <li key={i.id} className={`rounded-lg border ${SEV[i.severity].cls} ${i.status === "dismissed" ? "opacity-60" : ""}`}>
                <button className="flex w-full items-start gap-3 p-3 text-left" onClick={() => toggle(i.id)} aria-expanded={open.has(i.id)}>
                  <span className="mt-0.5 w-5 text-right text-xs text-muted tabular-nums">{n + 1}.</span>
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${SEV[i.severity].badge}`}>{SEV[i.severity].label}</span>
                  <span className="flex-1">
                    <span className="font-medium">{i.title}</span>
                    <span className="block text-sm text-muted">{i.observation}</span>
                  </span>
                  <span className="text-xs text-muted">{CATS[i.category] ?? i.category}</span>
                </button>
                {open.has(i.id) && (
                  <div className="grid gap-3 border-t border-line px-3 pb-3 pt-2 pl-11 text-sm md:grid-cols-2">
                    {i.evidence.length > 0 && (
                      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5 text-xs md:col-span-2">
                        {i.evidence.map(([k, v]) => <Fragment key={k}><dt className="text-muted">{k}</dt><dd>{v}</dd></Fragment>)}
                      </dl>
                    )}
                    <div><div className="text-xs font-semibold uppercase text-muted">Why it matters</div>{i.reasoning}</div>
                    <div><div className="text-xs font-semibold uppercase text-muted">What to do</div>{i.proposed_action}</div>
                    <div className="text-xs text-muted md:col-span-2">
                      Expected impact: {i.expected_impact} · confidence {Math.round(i.confidence * 100)}% · risk of the change: {i.risk}
                      {i.status === "dismissed" && <> · dismissed by {i.dismissed_by}{i.dismiss_note ? ` — “${i.dismiss_note}”` : ""}</>}
                    </div>
                    <div className="flex gap-2 md:col-span-2">
                      {i.link && <Link href={i.link} className="rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2">Open details →</Link>}
                      {i.status === "open"
                        ? <button onClick={() => setStatus(i, "dismissed")} className="rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2">Dismiss</button>
                        : <button onClick={() => setStatus(i, "open")} className="rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2">Restore</button>}
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ol>
          {!shown.length && <p className="py-6 text-center text-sm text-ok">No open issues 🎉</p>}
          <p className="mt-4 text-xs text-muted">The audit only reads data. Fixes are made by you in Google Ads / on the website (automatic changes come later with approvals).</p>
        </>
      )}
    </>
  );
}
