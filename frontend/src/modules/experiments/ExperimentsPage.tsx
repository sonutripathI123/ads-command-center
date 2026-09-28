"use client";
// P20 — Experiments: A/B and before/after tests measured from synced Google Ads data, approved through P16.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Row = { metric: string; control: number | null; variant: number | null; lift: number | null; p_value: number | null; test: string; direction?: string };
type Side = { label: string; impressions: number; clicks: number; cost: number; conversions: number };
type Results = { computed_on: string; periods: { control: [string, string]; variant: [string, string] }; control: Side; variant: Side;
  rows: Row[]; verdict: string; enough_data: boolean; primary_metric: string; limitations: string[] };
type Experiment = {
  id: number; name: string; hypothesis: string; change_description: string; kind: "a_b" | "before_after"; entity_type: string;
  control_ref: string; control_label: string | null; variant_ref: string | null; variant_label: string | null; primary_metric: string;
  baseline_start: string | null; baseline_end: string | null; start_date: string; end_date: string; min_clicks: number;
  status: string; approval_id: number | null; approval_status: string | null; results: Results | null; conclusion: string | null;
  created_by: string | null; created_at: string;
};
type Account = { id: number; customer_id: string; name: string };
type Entity = { ref: string; label: string; status: string; clicks_90d: number };
type Meta = { kinds: string[]; entity_types: string[]; metrics: { key: string; label: string; tested: boolean }[] };

const BASE = `${API_BASE}/api/v1/experiments`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const card = "rounded-lg border border-line bg-surface p-4";
const btn = "rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2 disabled:opacity-50";
const input = "mt-1 w-full rounded-md border border-line bg-surface px-2 py-1 text-sm text-fg";
const STATUS: Record<string, string> = { draft: "bg-surface-2 text-muted", pending_approval: "bg-warn/15 text-warn", running: "bg-accent-soft text-accent",
  completed: "bg-ok/15 text-ok", cancelled: "bg-surface-2 text-muted" };
const VERDICT: Record<string, [string, string]> = {
  variant_better: ["Variant is better (statistically significant)", "border-ok/30 bg-ok/10 text-ok"],
  control_better: ["Control is better (statistically significant)", "border-danger/30 bg-danger/10 text-danger"],
  no_significant_difference: ["No significant difference yet", "border-line bg-surface-2"],
  directional_variant_better: ["Variant looks better (directional — no significance test for cost metrics)", "border-ok/30 bg-ok/10 text-ok"],
  directional_control_better: ["Control looks better (directional — no significance test for cost metrics)", "border-warn/30 bg-warn/10 text-warn"],
  insufficient_data: ["Not enough data to decide", "border-warn/30 bg-warn/10 text-warn"],
};
const METRIC: Record<string, string> = { ctr: "CTR", conv_rate: "Conversion rate", avg_cpc: "Avg. CPC", cost_per_conversion: "Cost / conversion" };
const iso = (d: Date) => d.toISOString().slice(0, 10);
const addDays = (n: number) => { const d = new Date(); d.setDate(d.getDate() + n); return iso(d); };
const fmt = (m: string, v: number | null) => v === null ? "—" : m === "ctr" || m === "conv_rate" ? `${(v * 100).toFixed(2)}%` : `$${v.toFixed(2)}`;

function ResultsView({ r }: { r: Results }) {
  const [label, cls] = VERDICT[r.verdict] ?? [r.verdict, "border-line"];
  return (
    <div className="grid gap-3">
      <div className={`rounded-md border px-3 py-2 text-sm font-medium ${cls}`}>{label} · primary metric: {METRIC[r.primary_metric]}</div>
      <div className="grid gap-2 text-sm md:grid-cols-2">
        {(["control", "variant"] as const).map((k) => (
          <div key={k} className="rounded-md bg-surface-2 p-3">
            <div className="text-xs font-semibold uppercase text-muted">{k} · {r.periods[k][0]} → {r.periods[k][1]}</div>
            <div className="font-medium">{r[k].label}</div>
            <div className="text-xs text-muted tabular-nums">{r[k].impressions.toLocaleString()} impr · {r[k].clicks.toLocaleString()} clicks · ${r[k].cost.toFixed(2)} · {r[k].conversions} conv.</div>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-muted"><th className="py-1 pr-3">Metric</th><th className="pr-3 text-right">Control</th><th className="pr-3 text-right">Variant</th><th className="pr-3 text-right">Change</th><th className="pr-3 text-right">p-value</th><th>Test</th></tr></thead>
          <tbody>
            {r.rows.map((x) => (
              <tr key={x.metric} className={`border-t border-line ${x.metric === r.primary_metric ? "font-medium" : ""}`}>
                <td className="py-1 pr-3">{METRIC[x.metric]}</td>
                <td className="pr-3 text-right tabular-nums">{fmt(x.metric, x.control)}</td>
                <td className="pr-3 text-right tabular-nums">{fmt(x.metric, x.variant)}</td>
                <td className={`pr-3 text-right tabular-nums ${x.direction === "better" ? "text-ok" : x.direction === "worse" ? "text-danger" : ""}`}>
                  {x.lift === null ? "—" : `${x.lift > 0 ? "+" : ""}${(x.lift * 100).toFixed(1)}%`}{x.direction && x.direction !== "same" && <span className="sr-only"> ({x.direction})</span>}
                </td>
                <td className="pr-3 text-right tabular-nums">{x.p_value ?? "—"}</td>
                <td className="text-xs text-muted">{x.test}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {r.limitations.length > 0 && (
        <div className="text-sm"><div className="text-xs font-semibold uppercase text-muted">Limitations</div>
          <ul className="list-disc pl-5">{r.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul></div>
      )}
      <p className="text-[11px] text-muted">Computed {r.computed_on} from synced Google Ads data. Significant = p &lt; 0.05. Results are evidence, not a guarantee.</p>
    </div>
  );
}

function ExperimentForm({ accId, meta, onCreated, onCancel }: { accId: number; meta: Meta; onCreated: (e: Experiment) => void; onCancel: () => void }) {
  const [f, setF] = useState({ name: "", hypothesis: "", change_description: "", kind: "a_b", entity_type: "campaign", control_ref: "", variant_ref: "",
    primary_metric: "ctr", start_date: addDays(0), end_date: addDays(27), baseline_start: addDays(-28), baseline_end: addDays(-1), min_clicks: 100 });
  const [ents, setEnts] = useState<Entity[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: string | number) => setF((x) => ({ ...x, [k]: v }));

  useEffect(() => {
    call<Entity[]>(`/accounts/${accId}/entities?entity_type=${f.entity_type}`).then(setEnts).catch((e) => setErr((e as Error).message));
  }, [accId, f.entity_type]);

  async function submit() {
    setBusy(true); setErr(null);
    const ab = f.kind === "a_b";
    try {
      onCreated(await call<Experiment>(`/accounts/${accId}`, { method: "POST", body: JSON.stringify({
        ...f, variant_ref: ab ? f.variant_ref || null : null, baseline_start: ab ? null : f.baseline_start, baseline_end: ab ? null : f.baseline_end,
        min_clicks: Number(f.min_clicks) }) }));
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  const pick = (k: "control_ref" | "variant_ref", label: string) => (
    <label className="text-xs text-muted">{label}
      <select className={input} value={f[k]} onChange={(e) => set(k, e.target.value)}>
        <option value="">— choose —</option>
        {ents.map((x) => <option key={x.ref} value={x.ref}>{x.label} ({x.status.toLowerCase()}, {x.clicks_90d} clicks/90d)</option>)}
      </select>
    </label>
  );

  return (
    <section className={`${card} mb-4 grid gap-3`}>
      <h2 className="font-semibold">New experiment</h2>
      {err && <p className="text-sm text-danger">{err}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-xs text-muted">Name<input className={input} value={f.name} onChange={(e) => set("name", e.target.value)} maxLength={255} /></label>
        <div className="text-xs text-muted">Type
          <div className="mt-1 flex gap-3 text-sm text-fg">
            <label><input type="radio" checked={f.kind === "a_b"} onChange={() => set("kind", "a_b")} /> A/B (same dates)</label>
            <label><input type="radio" checked={f.kind === "before_after"} onChange={() => set("kind", "before_after")} /> Before / after</label>
          </div>
        </div>
        <label className="text-xs text-muted md:col-span-2">Hypothesis<input className={input} value={f.hypothesis} onChange={(e) => set("hypothesis", e.target.value)}
          placeholder="e.g. Fixed-price airport headlines will lift CTR" maxLength={4000} /></label>
        <label className="text-xs text-muted md:col-span-2">What changes<input className={input} value={f.change_description} onChange={(e) => set("change_description", e.target.value)}
          placeholder="e.g. New RSA in the variant ad group; control unchanged" maxLength={4000} /></label>
        <label className="text-xs text-muted">Compare
          <select className={input} value={f.entity_type} onChange={(e) => setF((x) => ({ ...x, entity_type: e.target.value, control_ref: "", variant_ref: "" }))}>
            {meta.entity_types.map((t) => <option key={t} value={t}>{t.replace("_", " ")}s</option>)}
          </select>
        </label>
        <label className="text-xs text-muted">Primary metric
          <select className={input} value={f.primary_metric} onChange={(e) => set("primary_metric", e.target.value)}>
            {meta.metrics.map((m) => <option key={m.key} value={m.key}>{m.label}{m.tested ? "" : " (directional)"}</option>)}
          </select>
        </label>
        {pick("control_ref", f.kind === "a_b" ? "Control" : "Campaign / ad group / ad that changed")}
        {f.kind === "a_b" && pick("variant_ref", "Variant")}
        {f.kind === "before_after" && <>
          <label className="text-xs text-muted">Baseline from<input type="date" className={input} value={f.baseline_start} onChange={(e) => set("baseline_start", e.target.value)} /></label>
          <label className="text-xs text-muted">Baseline to<input type="date" className={input} value={f.baseline_end} onChange={(e) => set("baseline_end", e.target.value)} /></label>
        </>}
        <label className="text-xs text-muted">Test from<input type="date" className={input} value={f.start_date} onChange={(e) => set("start_date", e.target.value)} /></label>
        <label className="text-xs text-muted">Test to<input type="date" className={input} value={f.end_date} onChange={(e) => set("end_date", e.target.value)} /></label>
        <label className="text-xs text-muted">Minimum clicks per side<input type="number" min={10} className={input} value={f.min_clicks} onChange={(e) => set("min_clicks", e.target.value)} /></label>
      </div>
      <div className="flex gap-2">
        <button className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50" disabled={busy || !f.name || !f.control_ref} onClick={submit}>
          {busy ? "Saving…" : "Save draft"}
        </button>
        <button className={btn} onClick={onCancel}>Cancel</button>
      </div>
    </section>
  );
}

function ExperimentDetail({ e, onChange, setMsg }: { e: Experiment; onChange: () => Promise<void>; setMsg: (m: { ok: boolean; text: string }) => void }) {
  const [preview, setPreview] = useState<Results | null>(null);
  const [conclusion, setConclusion] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  async function act(label: string, fn: () => Promise<unknown>, ok?: string) {
    setBusy(label);
    try { await fn(); if (ok) setMsg({ ok: true, text: ok }); await onChange(); }
    catch (x) { setMsg({ ok: false, text: (x as Error).message }); }
    finally { setBusy(null); }
  }
  const post = (p: string, body?: object) => call<unknown>(`/${e.id}/${p}`, { method: "POST", body: body ? JSON.stringify(body) : undefined });
  const results = e.status === "draft" || e.status === "pending_approval" ? preview : e.results ?? preview;

  return (
    <section className={`${card} grid gap-3`}>
      <div className="flex flex-wrap items-start gap-2">
        <div className="flex-1">
          <h2 className="font-semibold">{e.name}</h2>
          <p className="text-xs text-muted">{e.kind === "a_b" ? "A/B" : "Before / after"} · {e.entity_type.replace("_", " ")} · test {e.start_date} → {e.end_date}
            {e.kind === "before_after" && <> · baseline {e.baseline_start} → {e.baseline_end}</>} · min {e.min_clicks} clicks per side</p>
        </div>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${STATUS[e.status]}`}>{e.status.replace("_", " ")}</span>
      </div>
      {e.hypothesis && <p className="text-sm"><span className="text-muted">Hypothesis:</span> {e.hypothesis}</p>}
      {e.change_description && <p className="text-sm"><span className="text-muted">Change:</span> {e.change_description}</p>}
      <p className="text-sm"><span className="text-muted">Control:</span> {e.control_label}{e.variant_label && <> · <span className="text-muted">Variant:</span> {e.variant_label}</>}</p>

      <div className="flex flex-wrap gap-2">
        {e.status === "draft" && <>
          <button className="rounded-md bg-accent px-3 py-1 text-xs font-medium text-white disabled:opacity-50" disabled={!!busy}
            onClick={() => act("submit", () => post("submit"), "Sent to the Approval Center.")}>Submit for approval</button>
          <button className={btn} disabled={!!busy} onClick={() => act("preview", async () => setPreview(await post("analyze") as Results))}>
            {busy === "preview" ? "Calculating…" : "Preview results"}</button>
        </>}
        {e.status === "pending_approval" && <>
          <span className="text-xs text-muted">Approval: <b>{e.approval_status}</b> — decide it in the <Link href="/approvals" className="text-accent underline">Approval Center</Link>.</span>
          <button className="rounded-md bg-accent px-3 py-1 text-xs font-medium text-white disabled:opacity-50" disabled={!!busy}
            onClick={() => act("start", () => post("start"), "Experiment is running.")}>Start</button>
        </>}
        {e.status === "running" && (
          <button className={btn} disabled={!!busy} onClick={() => act("analyze", () => post("analyze"), "Results updated.")}>
            {busy === "analyze" ? "Calculating…" : "Update results"}</button>
        )}
        {!["completed", "cancelled"].includes(e.status) && (
          <button className={btn} disabled={!!busy} onClick={() => act("cancel", () => post("cancel"), "Experiment cancelled.")}>Cancel experiment</button>
        )}
      </div>

      {results && <ResultsView r={results} />}
      {e.status === "running" && (
        <div className="grid gap-2 rounded-md border border-line p-3">
          <label className="text-xs text-muted">Conclusion — what you learned and what you will do next
            <textarea className={input} rows={2} value={conclusion} onChange={(x) => setConclusion(x.target.value)} maxLength={4000} />
          </label>
          <button className="w-fit rounded-md bg-accent px-3 py-1 text-xs font-medium text-white disabled:opacity-50" disabled={!!busy || !conclusion.trim()}
            onClick={() => act("complete", () => post("complete", { conclusion }), "Experiment completed.")}>Complete experiment</button>
        </div>
      )}
      {e.conclusion && <p className="rounded-md bg-surface-2 p-3 text-sm"><span className="text-xs font-semibold uppercase text-muted">Conclusion</span><br />{e.conclusion}</p>}
    </section>
  );
}

export function ExperimentsPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [accId, setAccId] = useState<number | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [list, setList] = useState<Experiment[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    Promise.all([call<Account[]>("/accounts"), call<Meta>("/meta")]).then(([a, m]) => {
      setAccounts(a); setMeta(m); if (a[0]) setAccId(a[0].id);
    }).catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/experiments"); else setMsg({ ok: false, text: (e as Error).message }); });
  }, [router]);

  const load = useCallback(async () => {
    if (!accId) return;
    const l = await call<Experiment[]>(`/accounts/${accId}`);
    setList(l);
    setSel((s) => s ?? l[0]?.id ?? null);
  }, [accId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on selection change
    load().catch((e) => setMsg({ ok: false, text: (e as Error).message }));
  }, [load]);

  const current = list.find((x) => x.id === sel);

  return (
    <>
      <PageHeader title="Experiments" moduleId="P20">
        <div className="flex flex-wrap items-center gap-2">
          {accounts && accounts.length > 1 && (
            <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => { setAccId(Number(e.target.value)); setSel(null); }}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
            </select>
          )}
          <button onClick={() => setCreating(true)} disabled={!accId || creating} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">New experiment</button>
        </div>
      </PageHeader>
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      <p className="mb-4 text-sm text-muted">
        Test one change at a time. Results come from synced Google Ads data; CTR and conversion rate get a significance test.
        Running an experiment needs an approval in the <Link href="/approvals" className="text-accent underline">Approval Center</Link>. Nothing is changed in Google Ads from here.
      </p>
      {creating && accId && meta && (
        <ExperimentForm accId={accId} meta={meta} onCancel={() => setCreating(false)}
          onCreated={(e) => { setCreating(false); setSel(e.id); setMsg({ ok: true, text: `Draft “${e.name}” saved.` }); load(); }} />
      )}
      {accId && !list.length && !creating && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">No experiments yet. Click “New experiment”.</p>
      )}
      {list.length > 0 && (
        <div className="grid gap-4 md:grid-cols-[260px_1fr]">
          <ol className="grid content-start gap-1">
            {list.map((x) => (
              <li key={x.id}>
                <button onClick={() => setSel(x.id)} aria-current={x.id === sel}
                  className={`w-full rounded-md border px-3 py-2 text-left text-sm ${x.id === sel ? "border-accent bg-accent-soft" : "border-line bg-surface hover:bg-surface-2"}`}>
                  <span className="block truncate font-medium">{x.name}</span>
                  <span className="text-xs text-muted">{x.kind === "a_b" ? "A/B" : "Before/after"} · {x.status.replace("_", " ")}</span>
                </button>
              </li>
            ))}
          </ol>
          {current && <ExperimentDetail key={current.id} e={current} onChange={load} setMsg={setMsg} />}
        </div>
      )}
    </>
  );
}
