"use client";
// P09 — existing RSA analysis, AI/template ad writer with live checks, draft review, CSV export.
import { useRouter } from "next/navigation";
import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Finding = { field: string; index: number; text: string; code: string; severity: "error" | "warning"; message: string };
type Existing = { key: string; ad_group_name: string; campaign_name: string; status: string; headlines: string[]; descriptions: string[];
  final_urls: string[]; strength: number; findings: Finding[]; cost: number; clicks: number; ctr: number | null; conversions: number };
type Group = { google_id: string; name: string; campaign_name: string; status: string; keywords: string[]; keyword_count: number; final_url: string };
type Draft = { id: number; campaign_name: string; ad_group_name: string; ad_group_google_id: string | null; final_url: string; keywords: string[];
  usps: string[]; headlines: string[]; descriptions: string[]; path1: string; path2: string; notes: string; mode: string; model: string | null;
  strength: number; status: "draft" | "approved" | "rejected"; checks: Finding[]; reviewed_by: string | null; created_at: string };
type Account = { id: number; customer_id: string; name: string; ai_live: boolean };

const BASE = `${API_BASE}/api/v1/creatives`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}
const card = "rounded-lg border border-line bg-surface p-4";
const input = "w-full rounded-md border border-line bg-surface px-2 py-1.5 text-sm";
const btn = "rounded-md border border-line px-2.5 py-1 text-sm hover:bg-surface-2 disabled:opacity-50";
const primary = "rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50";
const Strength = ({ v }: { v: number }) => (
  <span className={`rounded-full px-2 py-0.5 text-xs tabular-nums ${v >= 85 ? "bg-ok/15 text-ok" : v >= 60 ? "bg-warn/15 text-warn" : "bg-danger/15 text-danger"}`}>{v}</span>
);
const money = (n: number) => new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD" }).format(n);

export function CreativesPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [accId, setAccId] = useState<number | null>(null);
  const [tab, setTab] = useState<"existing" | "write" | "drafts">("existing");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    call<Account[]>("/accounts").then((a) => { setAccounts(a); if (a[0]) setAccId(a[0].id); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/ads-assets"); else setMsg({ ok: false, text: (e as Error).message }); });
  }, [router]);
  const acc = accounts?.find((a) => a.id === accId);

  return (
    <>
      <PageHeader title="Ads & Assets" moduleId="P09">
        {accounts && accounts.length > 1 && (
          <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => setAccId(Number(e.target.value))}>
            {accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
          </select>
        )}
      </PageHeader>
      <div role="tablist" className="mb-4 flex w-fit overflow-hidden rounded-md border border-line">
        {([["existing", "Existing ads"], ["write", "✍ Write new ads"], ["drafts", "Drafts"]] as const).map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`px-3 py-1.5 text-sm ${tab === k ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"}`}>{l}</button>
        ))}
      </div>
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      {accId && tab === "existing" && <ExistingAds accId={accId} />}
      {accId && tab === "write" && <Writer accId={accId} aiLive={!!acc?.ai_live} onCreated={() => { setTab("drafts"); setMsg({ ok: true, text: "Draft created — review it below." }); }} />}
      {accId && tab === "drafts" && <Drafts accId={accId} />}
      <p className="mt-4 text-xs text-muted">Nothing here is published. Approved drafts export as a CSV for Google Ads Editor (imported as paused ads).</p>
    </>
  );
}

function ExistingAds({ accId }: { accId: number }) {
  const [rows, setRows] = useState<Existing[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { call<Existing[]>(`/accounts/${accId}/analysis`).then(setRows).catch(() => setRows([])); }, [accId]);
  if (!rows) return <p className="text-sm text-muted">Loading…</p>;
  if (!rows.length) return <p className="text-sm text-muted">No responsive search ads found — sync the account on the Campaigns page.</p>;
  return (
    <section className={card}>
      <h2 className="mb-2 font-semibold">Responsive search ads (weakest first)</h2>
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-muted"><tr><th className="py-1 font-medium">Ad group</th><th className="font-medium">Status</th><th className="text-right font-medium">Headlines</th>
          <th className="text-right font-medium">Descr.</th><th className="text-right font-medium">Cost (90d)</th><th className="text-right font-medium">CTR</th><th className="pl-3 font-medium">Strength*</th><th className="font-medium">Problems</th></tr></thead>
        <tbody className="divide-y divide-line">
          {rows.map((r) => (
            <Fragment key={r.key}>
              <tr className="cursor-pointer align-top hover:bg-surface-2" onClick={() => setOpen(open === r.key ? null : r.key)}>
                <td className="py-1.5">{r.ad_group_name}<div className="text-xs text-muted">{r.campaign_name}</div></td>
                <td className="text-xs">{r.status.toLowerCase()}</td>
                <td className="text-right tabular-nums">{r.headlines.length}/15</td><td className="text-right tabular-nums">{r.descriptions.length}/4</td>
                <td className="text-right tabular-nums">{money(r.cost)}</td><td className="text-right tabular-nums">{r.ctr !== null ? `${(r.ctr * 100).toFixed(1)}%` : "—"}</td>
                <td className="pl-3"><Strength v={r.strength} /></td>
                <td className="text-xs">{r.findings.length ? r.findings.slice(0, 2).map((f) => f.message).join("; ") + (r.findings.length > 2 ? ` +${r.findings.length - 2}` : "") : <span className="text-ok">none</span>}</td>
              </tr>
              {open === r.key && (
                <tr><td colSpan={8} className="bg-surface-2 p-3 text-xs">
                  <div className="grid gap-1 md:grid-cols-2">
                    <div>{r.headlines.map((h, i) => <div key={i}>H{i + 1}: {h} <span className="text-muted">({h.length})</span></div>)}</div>
                    <div>{r.descriptions.map((d, i) => <div key={i}>D{i + 1}: {d} <span className="text-muted">({d.length})</span></div>)}
                      <div className="mt-1 text-muted">{r.final_urls[0]}</div></div>
                  </div>
                </td></tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-muted">*Our estimate of Ad Strength from the rules below — Google&apos;s own rating isn&apos;t available with read-only access.</p>
    </section>
  );
}

function Writer({ accId, aiLive, onCreated }: { accId: number; aiLive: boolean; onCreated: () => void }) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [pick, setPick] = useState<string>("");
  const [f, setF] = useState({ ad_group_name: "", campaign_name: "", final_url: "", keywords: "", usps: "" });
  const [useAi, setUseAi] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { call<Group[]>(`/accounts/${accId}/ad-groups`).then(setGroups).catch(() => setGroups([])); }, [accId]);

  function choose(id: string) {
    setPick(id);
    const g = groups.find((x) => x.google_id === id);
    if (g) setF({ ...f, ad_group_name: g.name, campaign_name: g.campaign_name, final_url: g.final_url, keywords: g.keywords.slice(0, 10).join("\n") });
  }

  async function go() {
    setBusy(true); setErr(null);
    try {
      await call("/accounts/" + accId + "/drafts", { method: "POST", body: JSON.stringify({
        ad_group_name: f.ad_group_name, campaign_name: f.campaign_name, ad_group_google_id: pick || null, final_url: f.final_url,
        keywords: f.keywords.split("\n").map((s) => s.trim()).filter(Boolean), usps: f.usps.split("\n").map((s) => s.trim()).filter(Boolean), use_ai: useAi }) });
      onCreated();
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <section className={card}>
      <h2 className="mb-1 font-semibold">Write a new responsive search ad</h2>
      <p className="mb-3 text-xs text-muted">{aiLive ? "Claude writes 15 headlines and 4 descriptions from your keywords, areas and approved USPs; every line is then checked." : "AI is off — a template ad is generated from your keywords. Turn on live AI on the Recommendations page instructions."}</p>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-sm">Start from an existing ad group (optional)
          <select className={`${input} mt-1`} value={pick} onChange={(e) => choose(e.target.value)}>
            <option value="">— new ad group —</option>
            {groups.map((g) => <option key={g.google_id} value={g.google_id}>{g.name} ({g.keyword_count} keywords) — {g.campaign_name}</option>)}
          </select>
        </label>
        <label className="text-sm">Ad group name *<input className={`${input} mt-1`} value={f.ad_group_name} onChange={(e) => setF({ ...f, ad_group_name: e.target.value })} placeholder="e.g. Airport Transfers Melbourne" /></label>
        <label className="text-sm">Campaign<input className={`${input} mt-1`} value={f.campaign_name} onChange={(e) => setF({ ...f, campaign_name: e.target.value })} /></label>
        <label className="text-sm">Landing page (final URL)<input className={`${input} mt-1`} value={f.final_url} onChange={(e) => setF({ ...f, final_url: e.target.value })} placeholder="https://corporatecarsmelbourne.com.au/airport-transfers" /></label>
        <label className="text-sm">Main keywords (one per line)<textarea className={`${input} mt-1 h-28 font-mono text-xs`} value={f.keywords} onChange={(e) => setF({ ...f, keywords: e.target.value })} /></label>
        <label className="text-sm">Approved USPs / claims (one per line — only these may be claimed)
          <textarea className={`${input} mt-1 h-28 text-xs`} value={f.usps} onChange={(e) => setF({ ...f, usps: e.target.value })} placeholder={"Fixed price airport transfers\nFlight tracking & free waiting\nMercedes-Benz fleet\n15+ years in Melbourne"} />
        </label>
      </div>
      {err && <p className="mt-2 text-sm text-danger" role="alert">{err}</p>}
      <div className="mt-3 flex items-center gap-3">
        <button className={primary} onClick={go} disabled={busy || !f.ad_group_name.trim()}>{busy ? (useAi && aiLive ? "Claude is writing…" : "Generating…") : "Generate ad"}</button>
        {aiLive && <label className="flex items-center gap-1.5 text-sm"><input type="checkbox" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} /> Use Claude (≈ $0.05–0.15)</label>}
      </div>
    </section>
  );
}

function Drafts({ accId }: { accId: number }) {
  const [rows, setRows] = useState<Draft[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => call<Draft[]>(`/accounts/${accId}/drafts`).then(setRows).catch(() => setRows([])), [accId]);
  useEffect(() => { load(); }, [load]);
  if (!rows) return <p className="text-sm text-muted">Loading…</p>;
  return (
    <>
      <div className="mb-3 flex items-center gap-2">
        <a className={btn} href={`${BASE}/accounts/${accId}/drafts/export`}>Download approved (CSV)</a>
        {msg && <span className="text-sm text-danger">{msg}</span>}
      </div>
      {!rows.length && <p className="text-sm text-muted">No drafts yet — use “Write new ads”.</p>}
      <div className="grid gap-4">{rows.map((d) => <DraftEditor key={d.id} d={d} onSaved={load} onError={setMsg} />)}</div>
    </>
  );
}

function DraftEditor({ d, onSaved, onError }: { d: Draft; onSaved: () => void; onError: (m: string | null) => void }) {
  const [hs, setHs] = useState(d.headlines);
  const [ds, setDs] = useState(d.descriptions);
  const [paths, setPaths] = useState([d.path1, d.path2]);
  const [busy, setBusy] = useState(false);
  const byField = useMemo(() => {
    const m: Record<string, Finding[]> = {};
    for (const c of d.checks) (m[`${c.field}:${c.index}`] ??= []).push(c);
    return m;
  }, [d.checks]);
  const adLevel = d.checks.filter((c) => c.field === "ad");
  const errors = d.checks.filter((c) => c.severity === "error").length;
  const dirty = JSON.stringify([hs, ds, paths]) !== JSON.stringify([d.headlines, d.descriptions, [d.path1, d.path2]]);

  async function save(status?: string) {
    setBusy(true); onError(null);
    try {
      await call(`/drafts/${d.id}`, { method: "PATCH", body: JSON.stringify({ headlines: hs, descriptions: ds, path1: paths[0], path2: paths[1], ...(status ? { status } : {}) }) });
      onSaved();
    } catch (e) { onError((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <section className={`${card} ${d.status === "approved" ? "border-ok/40" : d.status === "rejected" ? "opacity-60" : ""}`}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{d.ad_group_name}</h3>
        <span className="text-xs text-muted">{d.campaign_name}</span>
        <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-muted">{d.mode === "live" ? `Claude ${d.model}` : d.mode}</span>
        <Strength v={d.strength} />
        <span className={`text-xs font-medium ${d.status === "approved" ? "text-ok" : d.status === "rejected" ? "text-muted" : "text-accent"}`}>{d.status}</span>
        <span className="ml-auto flex gap-2">
          {d.status === "draft" && <>
            <button className={btn} disabled={busy || !dirty} onClick={() => save()}>Save & re-check</button>
            <button className={primary} disabled={busy || dirty || errors > 0} title={errors ? "Fix red errors first" : ""} onClick={() => save("approved")}>Approve</button>
            <button className={btn} disabled={busy} onClick={() => save("rejected")}>Reject</button>
          </>}
          {d.status !== "draft" && <button className={btn} disabled={busy} onClick={() => save("draft")}>Back to draft</button>}
        </span>
      </div>
      {adLevel.length > 0 && <ul className="mb-3 text-xs">{adLevel.map((c, i) => <li key={i} className={c.severity === "error" ? "text-danger" : "text-warn"}>• {c.message}</li>)}</ul>}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="grid gap-1.5">{hs.map((h, i) => <Line key={i} checks={byField} disabled={d.status !== "draft"} field="headline" i={i} value={h} max={30} onChange={(v) => setHs(hs.map((x, j) => (j === i ? v : x)))} />)}</div>
        <div className="grid content-start gap-1.5">
          {ds.map((s, i) => <Line key={i} checks={byField} disabled={d.status !== "draft"} field="description" i={i} value={s} max={90} onChange={(v) => setDs(ds.map((x, j) => (j === i ? v : x)))} />)}
          {paths.map((p, i) => <Line key={`p${i}`} checks={byField} disabled={d.status !== "draft"} field="path" i={i} value={p} max={15} onChange={(v) => setPaths(paths.map((x, j) => (j === i ? v : x)))} />)}
          <div className="mt-2 rounded-md bg-surface-2 p-3 text-sm">
            <div className="text-xs text-muted">Preview</div>
            <div className="text-xs">Ad · {(d.final_url || "example.com").replace(/^https?:\/\//, "").split("/")[0]}/{paths.filter(Boolean).join("/")}</div>
            <div className="font-medium text-accent">{hs.slice(0, 3).join(" | ")}</div>
            <div className="text-xs">{ds.slice(0, 2).join(" ")}</div>
          </div>
          {d.notes && <p className="text-xs text-muted">Notes: {d.notes}</p>}
        </div>
      </div>
    </section>
  );
}

function Line({ field, i, value, max, onChange, checks, disabled }: {
  field: string; i: number; value: string; max: number; onChange: (v: string) => void; checks: Record<string, Finding[]>; disabled: boolean;
}) {
  const fs = checks[`${field}:${i}`] ?? [];
  const err = fs.some((f) => f.severity === "error");
  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="w-7 text-right text-xs text-muted">{field === "headline" ? "H" : field === "description" ? "D" : "P"}{i + 1}</span>
        <input className={`${input} ${err ? "border-danger" : fs.length ? "border-warn" : ""}`} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled} />
        <span className={`w-12 text-right text-xs tabular-nums ${value.length > max ? "text-danger" : "text-muted"}`}>{value.length}/{max}</span>
      </div>
      {fs.map((f, k) => <div key={k} className={`ml-9 text-xs ${f.severity === "error" ? "text-danger" : "text-warn"}`}>{f.message}</div>)}
    </div>
  );
}
