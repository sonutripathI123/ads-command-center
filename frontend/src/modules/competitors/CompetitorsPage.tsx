"use client";
// P11 — competitors: public-website observations, manual Google observations, coverage gaps and a separate interpretation.
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Obs = { id: number; competitor_id: number; kind: "serp" | "note"; source: string; observed_on: string; created_by: string | null;
  data: { query?: string; placement?: string; position?: number; text?: string } };
type Demand = { terms: number; impressions: number; clicks: number; cost: number; conversions: number;
  top: { search_term: string; impressions: number; clicks: number; cost: number }[] };
type Comp = { id: number; name: string; domain: string; base_url: string; notes: string; brand_terms: string[]; last_researched_at: string | null;
  research_notes: string[]; pages_read: number; themes: Record<string, string[]>; search_demand: Demand; observations: Obs[];
  messaging: { home_title: string; home_h1: string[]; home_description: string; headlines: string[]; ctas: string[]; prices: string[]; trust: string[] } };
type Cell = { pages: number; dedicated: number };
type Row = { term: string; us: Cell; competitors: Record<string, Cell> };
type Gaps = { gaps: { term: string; competitors: string[]; our_mentions: number }[]; advantages: { term: string; our_pages: number }[] };
type Interp = { summary: string; caveats: string[];
  competitors: { name: string; positioning: string; strengths: string[]; weaknesses: string[]; evidence: string[] }[];
  opportunities: { title: string; why: string; action: string; channel: string; evidence: string[] }[];
  messaging_angles: { headline_idea: string; rationale: string }[] };
type Analysis = { id: number; mode: "live" | "template"; model: string | null; created_at: string; created_by: string | null; observations_used: number; interpretation: Interp };
type Overview = { competitors: Comp[]; our_pages: number; our_sites: number; coverage: { services: Row[]; locations: Row[] };
  gaps: { services: Gaps; locations: Gaps }; research_enabled: boolean; ai_live: boolean; analysis: Analysis | null };
type Account = { id: number; customer_id: string; name: string; competitors: number };

const BASE = `${API_BASE}/api/v1/competitors`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = r.status === 204 ? null : await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

type Msg = { ok: boolean; text: string } | null;
const card = "rounded-lg border border-line bg-surface p-4";
const btn = "rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2 disabled:opacity-50";
const input = "mt-1 w-full rounded-md border border-line bg-surface px-2 py-1 text-sm text-fg";
const primary = "rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50";

function AddForm({ accId, onDone, onCancel }: { accId: number; onDone: (m: Msg) => void; onCancel: () => void }) {
  const [f, setF] = useState({ name: "", website: "", brand: "", notes: "" });
  const [err, setErr] = useState<string | null>(null);
  async function save() {
    setErr(null);
    try {
      await call(`/accounts/${accId}/competitors`, { method: "POST", body: JSON.stringify({ name: f.name, website: f.website, notes: f.notes,
        brand_terms: f.brand.split(",").map((s) => s.trim()).filter(Boolean) }) });
      onDone({ ok: true, text: `${f.name} added.` });
    } catch (e) { setErr((e as Error).message); }
  }
  return (
    <section className={`${card} mb-4 grid gap-3`}>
      <h2 className="font-semibold">Add competitor</h2>
      {err && <p className="text-sm text-danger">{err}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-xs text-muted">Name<input className={input} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} maxLength={255} /></label>
        <label className="text-xs text-muted">Website<input className={input} value={f.website} placeholder="example.com.au" onChange={(e) => setF({ ...f, website: e.target.value })} maxLength={512} /></label>
        <label className="text-xs text-muted">Other brand words people search (comma separated)
          <input className={input} value={f.brand} placeholder="e.g. short name, old name" onChange={(e) => setF({ ...f, brand: e.target.value })} /></label>
        <label className="text-xs text-muted">Notes<input className={input} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} maxLength={4000} /></label>
      </div>
      <div className="flex gap-2"><button className={primary} disabled={!f.name || !f.website} onClick={save}>Add</button><button className={btn} onClick={onCancel}>Cancel</button></div>
    </section>
  );
}

function ObservationForm({ compId, onDone }: { compId: number; onDone: (m: Msg) => void }) {
  const [f, setF] = useState({ kind: "serp", query: "", placement: "ad", position: "", text: "" });
  async function save() {
    try {
      const body = f.kind === "serp"
        ? { kind: "serp", query: f.query, placement: f.placement, position: f.position ? Number(f.position) : null, text: f.text || null }
        : { kind: "note", text: f.text };
      await call(`/competitors/${compId}/observations`, { method: "POST", body: JSON.stringify(body) });
      setF({ ...f, query: "", position: "", text: "" });
      onDone({ ok: true, text: "Observation saved." });
    } catch (e) { onDone({ ok: false, text: (e as Error).message }); }
  }
  return (
    <div className="grid gap-2 rounded-md border border-line p-3">
      <div className="flex flex-wrap gap-3 text-xs">
        <label><input type="radio" checked={f.kind === "serp"} onChange={() => setF({ ...f, kind: "serp" })} /> I saw them in Google</label>
        <label><input type="radio" checked={f.kind === "note"} onChange={() => setF({ ...f, kind: "note" })} /> Note</label>
      </div>
      {f.kind === "serp" && (
        <div className="grid gap-2 md:grid-cols-[2fr_1fr_1fr]">
          <label className="text-xs text-muted">What you searched<input className={input} value={f.query} onChange={(e) => setF({ ...f, query: e.target.value })} placeholder="chauffeur melbourne airport" maxLength={200} /></label>
          <label className="text-xs text-muted">Where
            <select className={input} value={f.placement} onChange={(e) => setF({ ...f, placement: e.target.value })}>
              <option value="ad">Sponsored ad</option><option value="organic">Normal result</option><option value="maps">Maps</option>
            </select>
          </label>
          <label className="text-xs text-muted">Position (optional)<input type="number" min={1} max={50} className={input} value={f.position} onChange={(e) => setF({ ...f, position: e.target.value })} /></label>
        </div>
      )}
      <label className="text-xs text-muted">{f.kind === "serp" ? "What their ad/result said (optional)" : "Note"}
        <input className={input} value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })} maxLength={2000} /></label>
      <button className={`${btn} w-fit`} disabled={f.kind === "serp" ? !f.query : !f.text} onClick={save}>Save observation</button>
    </div>
  );
}

function CompetitorCard({ c, researchOn, reload, setMsg }: { c: Comp; researchOn: boolean; reload: () => Promise<void>; setMsg: (m: Msg) => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [addObs, setAddObs] = useState(false);
  async function act(label: string, fn: () => Promise<unknown>, ok?: string) {
    setBusy(label);
    try { await fn(); if (ok) setMsg({ ok: true, text: ok }); await reload(); }
    catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(null); }
  }
  const research = () => act("research", async () => {
    const r = await call<{ pages_read: number; failed: string[]; notes: string[] }>(`/competitors/${c.id}/research`, { method: "POST" });
    setMsg({ ok: r.pages_read > 0, text: `${c.name}: read ${r.pages_read} public page(s).${r.failed.length ? ` ${r.failed.length} could not be read.` : ""} ${r.notes.join(" ")}` });
  });
  const m = c.messaging, d = c.search_demand;
  return (
    <li className={`${card} grid gap-3 text-sm`}>
      <div className="flex flex-wrap items-start gap-2">
        <div className="flex-1">
          <h3 className="font-semibold">{c.name} <a href={c.base_url} target="_blank" rel="noreferrer" className="text-xs font-normal text-accent underline">{c.domain}</a></h3>
          <p className="text-xs text-muted">{c.last_researched_at ? `Website read ${new Date(c.last_researched_at).toLocaleString("en-AU")} · ${c.pages_read} pages` : "Website not researched yet"}
            {c.research_notes.length > 0 && <> · {c.research_notes.join(" · ")}</>}{c.notes && <> · {c.notes}</>}</p>
        </div>
        <button className={btn} disabled={!!busy || !researchOn} onClick={research} title={researchOn ? "" : "Website research is switched off"}>
          {busy === "research" ? "Reading website…" : c.last_researched_at ? "Re-read website" : "Research website"}</button>
        <button className={btn} disabled={!!busy} onClick={() => act("archive", () => call(`/competitors/${c.id}`, { method: "PATCH", body: JSON.stringify({ status: "archived" }) }), `${c.name} archived.`)}>Archive</button>
      </div>
      {c.pages_read > 0 && (
        <div className="grid gap-2 md:grid-cols-2">
          <div className="rounded-md bg-surface-2 p-3">
            <div className="text-xs font-semibold uppercase text-muted">Their website says</div>
            <p className="font-medium">{m.home_h1[0] || m.home_title}</p>
            {m.home_description && <p className="text-xs text-muted">{m.home_description}</p>}
            <p className="mt-1 text-xs"><span className="text-muted">CTAs:</span> {m.ctas.join(", ") || "—"}</p>
            <p className="text-xs"><span className="text-muted">Prices shown:</span> {m.prices.join(", ") || "none"}</p>
            <p className="text-xs"><span className="text-muted">Trust signals:</span> {m.trust.join(", ").replace(/_/g, " ") || "none"}</p>
          </div>
          <div className="rounded-md bg-surface-2 p-3">
            <div className="text-xs font-semibold uppercase text-muted">Page themes</div>
            {Object.keys(c.themes).length ? (
              <ul className="text-xs">{Object.entries(c.themes).map(([t, urls]) => <li key={t}><b className="capitalize">{t}</b>: {urls.length} page{urls.length === 1 ? "" : "s"}</li>)}</ul>
            ) : <p className="text-xs text-muted">No themed pages among those read.</p>}
          </div>
        </div>
      )}
      <div className="rounded-md bg-surface-2 p-3 text-xs">
        <div className="font-semibold uppercase text-muted">Searches for “{c.name}” in your own account (12 months)</div>
        {d.terms ? <>
          <p>{d.terms} search terms · {d.impressions.toLocaleString()} impressions · {d.clicks} clicks · ${d.cost.toFixed(2)} spent · {d.conversions} conversions</p>
          <p className="text-muted">{d.top.slice(0, 5).map((t) => t.search_term).join(" · ")}</p>
        </> : <p className="text-muted">None — your ads haven&apos;t shown for searches naming them{c.brand_terms.length ? "" : " (add brand words if people know them by another name)"}.</p>}
      </div>
      <div>
        <div className="mb-1 flex items-center gap-2">
          <span className="text-xs font-semibold uppercase text-muted">Your observations</span>
          <button className={btn} onClick={() => setAddObs((v) => !v)}>{addObs ? "Close" : "Add"}</button>
        </div>
        {addObs && <ObservationForm compId={c.id} onDone={(msg) => { setMsg(msg); if (msg?.ok) reload(); }} />}
        <ul className="mt-2 grid gap-1 text-xs">
          {c.observations.map((o) => (
            <li key={o.id} className="flex flex-wrap items-center gap-2">
              <span className="text-muted">{o.observed_on}</span>
              <span className="flex-1">{o.kind === "serp" ? <>Searched “{o.data.query}” → {o.data.placement === "ad" ? "sponsored ad" : o.data.placement === "maps" ? "maps" : "normal result"}{o.data.position ? ` #${o.data.position}` : ""}{o.data.text && <> — “{o.data.text}”</>}</> : o.data.text}</span>
              <button className="text-muted underline" onClick={() => act(`d${o.id}`, () => call(`/observations/${o.id}`, { method: "DELETE" }))}>delete</button>
            </li>
          ))}
          {!c.observations.length && !addObs && <li className="text-muted">None yet. Search Google yourself and note who shows up.</li>}
        </ul>
      </div>
    </li>
  );
}

function CoverageTable({ rows, comps, gaps }: { rows: Row[]; comps: Comp[]; gaps: Gaps }) {
  const researched = comps.filter((c) => c.pages_read > 0);
  const gapSet = new Set(gaps.gaps.map((g) => g.term));
  const show = rows.filter((r) => r.us.pages || Object.values(r.competitors).some((v) => v.pages));
  const cellText = (v?: Cell) => (!v || !v.pages ? "—" : v.dedicated ? `${v.dedicated} page${v.dedicated === 1 ? "" : "s"} ★` : `mentioned (${v.pages})`);
  if (!researched.length) return <p className="text-sm text-muted">Research at least one competitor website to compare coverage.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs text-muted"><th className="py-1 pr-3">Term</th><th className="pr-3">You</th>{researched.map((c) => <th key={c.id} className="pr-3">{c.name}</th>)}</tr></thead>
        <tbody>
          {show.map((r) => (
            <tr key={r.term} className={`border-t border-line ${gapSet.has(r.term) ? "bg-warn/10" : ""}`}>
              <td className="py-1 pr-3 capitalize">{r.term}{gapSet.has(r.term) && <span className="ml-1 rounded bg-warn/15 px-1 text-[10px] font-semibold uppercase text-warn">gap</span>}</td>
              <td className="pr-3">{cellText(r.us)}</td>
              {researched.map((c) => <td key={c.id} className="pr-3">{cellText(r.competitors[String(c.id)])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-1 text-[11px] text-muted">★ = a page dedicated to it (in the URL, title or main heading). Gap = a competitor has one and you don&apos;t. Based only on the pages read.</p>
    </div>
  );
}

function Ev({ ev }: { ev: string[] }) {
  return ev.length ? <span className="ml-1 text-[10px] text-muted">[{ev.join(", ")}]</span> : null;
}

function InterpretationView({ a }: { a: Analysis }) {
  const x = a.interpretation;
  return (
    <div className="grid gap-3 text-sm">
      <p className="rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-xs">
        <b>Interpretation, not fact.</b> {a.mode === "live" ? `Written by Claude (${a.model})` : "Rule-based (AI off)"} from {a.observations_used} observations
        on {new Date(a.created_at).toLocaleString("en-AU")}. Evidence keys in [brackets] point to the facts above.
      </p>
      <p>{x.summary}</p>
      {x.opportunities.length > 0 && <div><div className="text-xs font-semibold uppercase text-muted">Opportunities</div>
        <ol className="grid gap-2">{x.opportunities.map((o, i) => (
          <li key={i} className="rounded-md bg-surface-2 p-2"><div className="font-medium">{i + 1}. {o.title} <span className="text-xs font-normal text-muted">· {o.channel}</span><Ev ev={o.evidence} /></div>
            <div className="text-xs text-muted">{o.why}</div><div className="mt-1">{o.action}</div></li>))}</ol></div>}
      {x.competitors.length > 0 && <div className="grid gap-2 md:grid-cols-2">{x.competitors.map((c, i) => (
        <div key={i} className="rounded-md border border-line p-2"><div className="font-medium">{c.name}<Ev ev={c.evidence} /></div>
          <p className="text-xs text-muted">{c.positioning}</p>
          {c.strengths.length > 0 && <p className="text-xs"><span className="text-muted">Strengths:</span> {c.strengths.join("; ")}</p>}
          {c.weaknesses.length > 0 && <p className="text-xs"><span className="text-muted">Weaknesses:</span> {c.weaknesses.join("; ")}</p>}</div>))}</div>}
      {x.messaging_angles.length > 0 && <div><div className="text-xs font-semibold uppercase text-muted">Messages to test</div>
        <ul className="list-disc pl-5">{x.messaging_angles.map((m, i) => <li key={i}><b>{m.headline_idea}</b> — <span className="text-muted">{m.rationale}</span></li>)}</ul></div>}
      {x.caveats.length > 0 && <ul className="list-disc pl-5 text-xs text-muted">{x.caveats.map((c, i) => <li key={i}>{c}</li>)}</ul>}
    </div>
  );
}

export function CompetitorsPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [accId, setAccId] = useState<number | null>(null);
  const [ov, setOv] = useState<Overview | null>(null);
  const [adding, setAdding] = useState(false);
  const [covTab, setCovTab] = useState<"services" | "locations">("services");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<Msg>(null);

  useEffect(() => {
    call<Account[]>("/accounts").then((a) => { setAccounts(a); if (a[0]) setAccId(a[0].id); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/competitors"); else setMsg({ ok: false, text: (e as Error).message }); });
  }, [router]);

  const load = useCallback(async () => { if (accId) setOv(await call<Overview>(`/accounts/${accId}`)); }, [accId]);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on selection change
    load().catch((e) => setMsg({ ok: false, text: (e as Error).message }));
  }, [load]);

  async function interpretNow() {
    setBusy(true); setMsg(null);
    try { await call(`/accounts/${accId}/analyze`, { method: "POST", body: JSON.stringify({ use_ai: true }) }); await load(); setMsg({ ok: true, text: "Interpretation ready." }); }
    catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(false); }
  }

  const gaps = ov ? ov.gaps[covTab] : null;
  return (
    <>
      <PageHeader title="Competitors" moduleId="P11">
        <div className="flex flex-wrap items-center gap-2">
          {accounts && accounts.length > 1 && (
            <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => setAccId(Number(e.target.value))}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
            </select>
          )}
          <button className={`${btn} py-1.5 text-sm`} disabled={!accId || adding} onClick={() => setAdding(true)}>Add competitor</button>
          <button className={primary} disabled={!accId || busy || !ov?.competitors.length} onClick={interpretNow}>
            {busy ? (ov?.ai_live ? "Claude is thinking…" : "Building…") : "Interpret findings"}</button>
        </div>
      </PageHeader>
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      <p className="mb-4 text-sm text-muted">
        Only public information: what competitors&apos; websites say, what you saw in Google yourself, and searches naming them in <i>your own</i> account.
        Nobody outside a competitor&apos;s Google Ads account can see their budgets, keywords or results — this page never claims to.
      </p>
      {ov && !ov.research_enabled && (
        <p className="mb-4 rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm">
          Reading competitor websites is switched off. To switch it on (owner): <code>python -m app.shared.flags_cli set competitor.research.enabled on --reason &quot;…&quot; --by you</code>.
          Manual observations work without it.
        </p>
      )}
      {adding && accId && <AddForm accId={accId} onCancel={() => setAdding(false)} onDone={(m) => { setAdding(false); setMsg(m); load(); }} />}
      {ov && !ov.competitors.length && !adding && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">No competitors yet. Click “Add competitor” — name and website.</p>
      )}
      {ov && ov.competitors.length > 0 && <>
        <ol className="mb-4 grid gap-3">
          {ov.competitors.map((c) => <CompetitorCard key={c.id} c={c} researchOn={ov.research_enabled} reload={load} setMsg={setMsg} />)}
        </ol>
        <section className={`${card} mb-4`}>
          <div className="mb-2 flex flex-wrap items-center gap-3">
            <h2 className="font-semibold">Coverage — you vs them</h2>
            <div role="tablist" className="flex overflow-hidden rounded-md border border-line">
              {(["services", "locations"] as const).map((k) => (
                <button key={k} role="tab" aria-selected={covTab === k} onClick={() => setCovTab(k)}
                  className={`px-3 py-1 text-sm capitalize ${covTab === k ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"}`}>{k}</button>
              ))}
            </div>
            <span className="text-xs text-muted">Your side: {ov.our_pages} crawled pages from {ov.our_sites} linked website(s).</span>
          </div>
          {gaps && gaps.gaps.length > 0 && <p className="mb-2 text-sm"><b>Gaps:</b> {gaps.gaps.map((g) => `${g.term} (${g.competitors.join(", ")})`).join(" · ")}</p>}
          {gaps && gaps.advantages.length > 0 && <p className="mb-2 text-sm"><b>Only you:</b> {gaps.advantages.map((g) => g.term).join(" · ")}</p>}
          <CoverageTable rows={ov.coverage[covTab]} comps={ov.competitors} gaps={ov.gaps[covTab]} />
        </section>
        <section className={card}>
          <h2 className="mb-2 font-semibold">Interpretation</h2>
          {ov.analysis ? <InterpretationView a={ov.analysis} /> : <p className="text-sm text-muted">Click “Interpret findings” after researching competitors and adding observations.</p>}
        </section>
      </>}
    </>
  );
}
