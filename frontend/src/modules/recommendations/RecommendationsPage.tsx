"use client";
// P14 — prioritised recommendations (from the P07 audit), decisions, and the AI action plan.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Rec = {
  id: number; category: string; severity: "critical" | "warning" | "info"; priority: number; title: string; observation: string;
  evidence: [string, string][]; reasoning: string; proposed_action: string; expected_impact: string; confidence: number; risk: string;
  requires_approval: boolean; link: string | null; status: string; decided_by: string | null; decision_note: string | null;
};
type Action = { title: string; why: string; steps: string[]; owner: string; effort: string; recommendation_ids: number[] };
type Plan = { summary: string; top_actions: Action[]; thirty_day_plan: { week: number; focus: string; tasks: string[] }[]; measure: string[]; caveats: string[] };
type Run = { id: number; mode: "live" | "template"; model: string | null; status: string; plan: Plan | null; error: string | null;
  created_by: string | null; created_at: string; output_tokens: number | null };
type AIStatus = { flag_enabled: boolean; api_key_configured: boolean; live: boolean; model: string };
type Account = { id: number; customer_id: string; name: string; open: number };

const BASE = `${API_BASE}/api/v1/recommendations`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const TABS = [["proposed", "To do"], ["accepted", "In progress"], ["done", "Done"], ["rejected", "Rejected"]] as const;
const SEV = { critical: "bg-danger/15 text-danger", warning: "bg-warn/15 text-warn", info: "bg-surface-2 text-muted" } as const;
const card = "rounded-lg border border-line bg-surface p-4";

export function RecommendationsPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [accId, setAccId] = useState<number | null>(null);
  const [tab, setTab] = useState<string>("proposed");
  const [recs, setRecs] = useState<Rec[]>([]);
  const [open, setOpen] = useState<Set<number>>(new Set());
  const [ai, setAi] = useState<AIStatus | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    Promise.all([call<Account[]>("/accounts"), call<AIStatus>("/ai-status")]).then(([a, s]) => {
      setAccounts(a); setAi(s); if (a[0]) setAccId(a[0].id);
    }).catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/recommendations"); else setMsg({ ok: false, text: (e as Error).message }); });
  }, [router]);

  const load = useCallback(async () => {
    if (!accId) return;
    const [r, p] = await Promise.all([call<Rec[]>(`/accounts/${accId}?status=${tab}`), call<{ run: Run | null }>(`/accounts/${accId}/plan`)]);
    setRecs(r); setRun(p.run);
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

  const refresh = () => act("refresh", async () => {
    const r = await call<{ new: number; superseded: number; total: number }>(`/accounts/${accId}/refresh`, { method: "POST" });
    setMsg({ ok: true, text: `${r.total} findings from the latest audit · ${r.new} new · ${r.superseded} no longer reported.` });
  });
  const decide = (r: Rec, status: string) => act(`s${r.id}`, () => call(`/${r.id}/status`, { method: "POST", body: JSON.stringify({ status }) }));
  const plan = () => act("plan", () => call<Run>(`/accounts/${accId}/plan`, { method: "POST" }));
  const toggle = (id: number) => setOpen((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const btn = "rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2 disabled:opacity-50";

  return (
    <>
      <PageHeader title="AI Recommendations" moduleId="P14">
        <div className="flex flex-wrap items-center gap-2">
          {accounts && accounts.length > 1 && (
            <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => setAccId(Number(e.target.value))}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
            </select>
          )}
          <Link href="/audit" className="rounded-md border border-line px-3 py-1.5 text-sm hover:bg-surface-2">Open audit</Link>
          <button onClick={refresh} disabled={!accId || !!busy} className="rounded-md border border-line px-3 py-1.5 text-sm hover:bg-surface-2 disabled:opacity-50">
            {busy === "refresh" ? "Refreshing…" : "Refresh from latest audit"}
          </button>
        </div>
      </PageHeader>
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}

      <section className={`${card} mb-4`}>
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <h2 className="font-semibold">Action plan</h2>
            <p className="text-xs text-muted">
              {ai?.live ? <>Written by Claude ({ai.model}) from your audit evidence.</>
                : <>AI is off — a rule-based plan is shown. To turn on Claude: add <code>ANTHROPIC_API_KEY</code> to backend/.env and run
                  {" "}<code>python -m app.shared.flags_cli set ai.live_calls.enabled on --reason &quot;…&quot;</code>.</>}
            </p>
          </div>
          <button onClick={plan} disabled={!accId || !!busy} className="ml-auto rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
            {busy === "plan" ? (ai?.live ? "Claude is writing…" : "Building…") : run ? "Regenerate plan" : "Generate plan"}
          </button>
        </div>
        {run?.status === "failed" && <p className="mt-3 text-sm text-danger">Plan failed: {run.error}</p>}
        {run?.plan && (
          <div className="mt-3 grid gap-4">
            <p className="text-sm">{run.plan.summary}</p>
            <ol className="grid gap-2">
              {run.plan.top_actions.map((a, n) => (
                <li key={n} className="rounded-md border border-line p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{n + 1}. {a.title}</span>
                    <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-muted">{a.owner}</span>
                    <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-muted">effort: {a.effort}</span>
                  </div>
                  <p className="mt-1 text-muted">{a.why}</p>
                  <ul className="mt-1 list-disc pl-5">{a.steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </li>
              ))}
            </ol>
            <div className="grid gap-3 md:grid-cols-4">
              {run.plan.thirty_day_plan.map((w) => (
                <div key={w.week} className="rounded-md bg-surface-2 p-3 text-sm">
                  <div className="text-xs text-muted">Week {w.week}</div><div className="font-medium">{w.focus}</div>
                  <ul className="mt-1 list-disc pl-4 text-xs">{w.tasks.map((t, i) => <li key={i}>{t}</li>)}</ul>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted">
              Measure: {run.plan.measure.join(" · ")}{run.plan.caveats.length > 0 && <> · {run.plan.caveats.join(" ")}</>}
              <br />{run.mode === "live" ? `Claude ${run.model}` : "Rule-based"} · {new Date(run.created_at).toLocaleString("en-AU")} · by {run.created_by}.
              Forecasts are never guaranteed.
            </p>
          </div>
        )}
      </section>

      <div role="tablist" className="mb-3 flex w-fit overflow-hidden rounded-md border border-line">
        {TABS.map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`px-3 py-1 text-sm ${tab === k ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"}`}>{l}</button>
        ))}
      </div>
      {!recs.length && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">
          {tab === "proposed" ? <>Nothing to do here. Run an <Link className="text-accent underline" href="/audit">audit</Link>, then click “Refresh from latest audit”.</> : "Nothing here."}
        </p>
      )}
      <ol className="grid gap-2">
        {recs.map((r) => (
          <li key={r.id} className="rounded-lg border border-line bg-surface">
            <button className="flex w-full items-start gap-3 p-3 text-left" onClick={() => toggle(r.id)} aria-expanded={open.has(r.id)}>
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${SEV[r.severity]}`}>{r.severity}</span>
              <span className="flex-1"><span className="font-medium">{r.title}</span><span className="block text-sm text-muted">{r.observation}</span></span>
              {r.requires_approval && <span className="rounded bg-accent-soft px-1.5 py-0.5 text-[10px] text-accent">changes Google Ads</span>}
              <span className="text-xs tabular-nums text-muted">P{r.priority}</span>
            </button>
            {open.has(r.id) && (
              <div className="grid gap-3 border-t border-line px-3 pb-3 pt-2 text-sm md:grid-cols-2">
                {r.evidence.length > 0 && (
                  <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5 text-xs md:col-span-2">
                    {r.evidence.map(([k, v]) => <Fragment key={k}><dt className="text-muted">{k}</dt><dd>{v}</dd></Fragment>)}
                  </dl>
                )}
                <div><div className="text-xs font-semibold uppercase text-muted">Why</div>{r.reasoning}</div>
                <div><div className="text-xs font-semibold uppercase text-muted">What to do</div>{r.proposed_action}</div>
                <div className="text-xs text-muted md:col-span-2">
                  Impact: {r.expected_impact} · confidence {Math.round(r.confidence * 100)}% · risk {r.risk}
                  {r.decided_by && <> · last decision by {r.decided_by}</>}
                  {r.requires_approval && <> · When automatic changes arrive (P16/P17), this will need an approval before anything is sent to Google Ads.</>}
                </div>
                <div className="flex flex-wrap gap-2 md:col-span-2">
                  {r.link && <Link href={r.link} className={btn}>Open details →</Link>}
                  {r.status === "proposed" && <><button className={btn} disabled={!!busy} onClick={() => decide(r, "accepted")}>Accept — I&apos;ll do it</button>
                    <button className={btn} disabled={!!busy} onClick={() => decide(r, "rejected")}>Reject</button></>}
                  {r.status === "accepted" && <><button className={btn} disabled={!!busy} onClick={() => decide(r, "done")}>Mark done</button>
                    <button className={btn} disabled={!!busy} onClick={() => decide(r, "proposed")}>Back to To do</button></>}
                  {(r.status === "rejected" || r.status === "done") && <button className={btn} disabled={!!busy} onClick={() => decide(r, r.status === "done" ? "accepted" : "proposed")}>Reopen</button>}
                </div>
              </div>
            )}
          </li>
        ))}
      </ol>
    </>
  );
}
