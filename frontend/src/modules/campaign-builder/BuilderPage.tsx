"use client";
// P15 — build a themed campaign draft from existing keywords, edit it, write ads per ad group, approve, export.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Kw = { text: string; match_type: string; cost: number; clicks: number; conversions: number };
type Group = { key: string; theme: string; name: string; keywords: Kw[]; reserve: Kw[]; final_url: string; landing_score: number;
  landing_reason: string; ad_draft_id: number | null; ad_status: string | null; ad_strength: number | null; ad_headlines: string[] };
type Check = { key: string; label: string; status: "pass" | "fail" | "manual"; detail: string };
type Draft = { id: number; name: string; goal: string; status: string; settings: { daily_budget: number; bidding: { strategy: string; max_cpc?: number };
  bidding_reason: string; networks: Record<string, boolean>; locations: string[]; status: string };
  ad_groups: Group[]; unassigned: Kw[]; negatives: { text: string; match_type: string; reason: string }[]; checklist: Check[];
  tracking_issues: string[]; created_by: string | null; approved_by: string | null; source: { keywords_in: number } };
type Account = { id: number; customer_id: string; name: string; websites: { id: number; name: string }[];
  ad_groups: { google_id: string; name: string; campaign_name: string; status: string; keywords: number }[]; themes: { key: string; label: string }[] };

const BASE = `${API_BASE}/api/v1/campaign-builder`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}
const card = "rounded-lg border border-line bg-surface p-4";
const input = "rounded-md border border-line bg-surface px-2 py-1 text-sm";
const btn = "rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2 disabled:opacity-50";
const primary = "rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50";
const ICON = { pass: "✓", fail: "✗", manual: "☐" } as const;
const TONE = { pass: "text-ok", fail: "text-danger", manual: "text-warn" } as const;

export function BuilderPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [acc, setAcc] = useState<Account | null>(null);
  const [list, setList] = useState<{ id: number; name: string; status: string }[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    call<Account[]>("/accounts").then((a) => { setAccounts(a); setAcc(a[0] ?? null); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/campaign-builder"); else setMsg({ ok: false, text: (e as Error).message }); });
  }, [router]);

  const loadList = useCallback(async (openFirst: boolean) => {
    if (!acc) return;
    const l = await call<{ id: number; name: string; status: string }[]>(`/accounts/${acc.id}/drafts`);
    setList(l);
    if (openFirst && l[0]) setDraft(await call<Draft>(`/drafts/${l[0].id}`));
  }, [acc]);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load
    loadList(true).catch(() => undefined);
  }, [loadList]);

  async function run(label: string, fn: () => Promise<Draft | void>, ok?: string) {
    setBusy(label); setMsg(null);
    try { const d = await fn(); if (d) setDraft(d); if (ok) setMsg({ ok: true, text: ok }); }
    catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(null); }
  }
  const edit = (op: Record<string, unknown>) => draft && run("edit", () => call<Draft>(`/drafts/${draft.id}`, { method: "PATCH", body: JSON.stringify(op) }));

  return (
    <>
      <PageHeader title="Campaign Builder" moduleId="P15">
        {list.length > 0 && (
          <select aria-label="Campaign draft" className={input} value={draft?.id ?? ""} onChange={(e) => run("open", () => call<Draft>(`/drafts/${e.target.value}`))}>
            {list.map((l) => <option key={l.id} value={l.id}>#{l.id} {l.name} ({l.status})</option>)}
          </select>
        )}
      </PageHeader>
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      {acc && <BuildForm acc={acc} busy={busy === "build"} onBuild={(body) => run("build", async () => {
        const d = await call<Draft>(`/accounts/${acc.id}/drafts`, { method: "POST", body: JSON.stringify(body) });
        await loadList(false); return d;
      }, "Draft built — review the ad groups below.")} />}
      {accounts && !accounts.length && <p className="text-sm text-muted">Connect a Google Ads account first.</p>}
      {draft && <DraftView d={draft} busy={busy} edit={edit} run={run} />}
      <p className="mt-4 text-xs text-muted">Everything here is a draft. The export imports into Google Ads Editor as a <b>paused</b> campaign; nothing is sent to Google Ads from this dashboard.</p>
    </>
  );
}

function BuildForm({ acc, busy, onBuild }: { acc: Account; busy: boolean; onBuild: (b: Record<string, unknown>) => void }) {
  const [open, setOpen] = useState(false);
  const [src, setSrc] = useState<string[]>([]);
  const [themes, setThemes] = useState<string[]>([]);
  const [f, setF] = useState({ name: "Search | Restructured (draft)", budget: "20", cpc: "3.25" });
  const toggle = (arr: string[], v: string) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
  if (!open) return <button className={`${primary} mb-4`} onClick={() => setOpen(true)}>+ Build a new campaign draft</button>;
  return (
    <section className={`${card} mb-4`}>
      <h2 className="mb-2 font-semibold">Build a campaign draft</h2>
      <p className="mb-3 text-xs text-muted">Pick the ad group(s) whose keywords you want to reorganise. They are grouped by service (airport, corporate, wedding…), unwanted ones become negatives, and each group gets its best landing page.</p>
      <div className="grid gap-3 md:grid-cols-2">
        <div className="text-sm">Source ad groups (none = all)
          <div className="mt-1 max-h-44 overflow-y-auto rounded-md border border-line p-2 text-xs">
            {acc.ad_groups.map((g) => (
              <label key={g.google_id} className="flex items-center gap-2 py-0.5">
                <input type="checkbox" checked={src.includes(g.google_id)} onChange={() => setSrc(toggle(src, g.google_id))} />
                {g.name} <span className="text-muted">· {g.keywords} keywords · {g.campaign_name || "campaign"} · {g.status.toLowerCase()}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="grid content-start gap-2 text-sm">
          <label>Campaign name<input className={`${input} mt-1 w-full`} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
          <div className="flex gap-2">
            <label className="flex-1">Daily budget (AUD)<input className={`${input} mt-1 w-full`} type="number" min={1} value={f.budget} onChange={(e) => setF({ ...f, budget: e.target.value })} /></label>
            <label className="flex-1">Max CPC (AUD)<input className={`${input} mt-1 w-full`} type="number" min={0.1} step={0.05} value={f.cpc} onChange={(e) => setF({ ...f, cpc: e.target.value })} /></label>
          </div>
          <div>Themes (none = all)
            <div className="mt-1 flex flex-wrap gap-1">
              {acc.themes.map((t) => (
                <button key={t.key} onClick={() => setThemes(toggle(themes, t.key))}
                  className={`rounded-full border px-2 py-0.5 text-xs ${themes.includes(t.key) ? "border-accent bg-accent-soft text-accent" : "border-line"}`}>{t.label}</button>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <button className={primary} disabled={busy || !f.name.trim()} onClick={() => onBuild({ name: f.name, source_ad_groups: src, themes: themes.length ? themes : null,
          daily_budget: Number(f.budget) || 20, max_cpc: Number(f.cpc) || 3 })}>{busy ? "Building…" : "Build draft"}</button>
        <button className={btn} onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </section>
  );
}

function DraftView({ d, busy, edit, run }: { d: Draft; busy: string | null; edit: (op: Record<string, unknown>) => void;
  run: (label: string, fn: () => Promise<Draft | void>, ok?: string) => void }) {
  const [usps, setUsps] = useState("");
  const [neg, setNeg] = useState("");
  const [showNeg, setShowNeg] = useState(false);
  const locked = d.status !== "draft";
  const groupKeys = d.ad_groups.map((g) => g.key);
  const writeAds = (g: Group) => run(`ads-${g.key}`, () => call<Draft>(`/drafts/${d.id}/ad-groups/${g.key}/write-ads`, {
    method: "POST", body: JSON.stringify({ usps: usps.split("\n").map((s) => s.trim()).filter(Boolean), use_ai: true }) }),
    `Ad written for ${g.name} — approve it on Ads & Assets → Drafts.`);

  return (
    <>
      <section className={`${card} mb-4`}>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">{d.name}</h2>
          <span className={`text-xs font-medium ${d.status === "approved" ? "text-ok" : "text-accent"}`}>{d.status}</span>
          <span className="text-xs text-muted">{d.source.keywords_in} keywords in · {d.ad_groups.length} ad groups · {d.negatives.length} negatives</span>
          <span className="ml-auto flex gap-2">
            {d.status === "draft" && <button className={primary} disabled={!!busy} onClick={() => edit({ op: "status", status: "approved" })}>Approve draft</button>}
            {d.status === "approved" && <>
              <a className={primary} href={`${BASE}/drafts/${d.id}/export`}>Download for Google Ads Editor</a>
              <button className={btn} disabled={!!busy} onClick={() => edit({ op: "status", status: "draft" })}>Back to draft</button></>}
            <button className={btn} disabled={!!busy} onClick={() => confirm("Archive this draft?") && edit({ op: "status", status: "archived" })}>Archive</button>
          </span>
        </div>
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          <div className="text-sm">
            <div className="font-medium">Settings</div>
            <div className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
              <span className="text-muted">Status</span><span>Paused (always)</span>
              <span className="text-muted">Networks</span><span>Google Search only (no partners, no Display)</span>
              <span className="text-muted">Bidding</span><span>{d.settings.bidding.strategy === "MAXIMIZE_CLICKS" ? `Maximize clicks, max CPC AUD ${d.settings.bidding.max_cpc}` : "Maximize conversions"} — {d.settings.bidding_reason}</span>
              <span className="text-muted">Budget</span>
              <span><input className={`${input} w-24 text-xs`} type="number" disabled={locked} defaultValue={d.settings.daily_budget}
                onBlur={(e) => Number(e.target.value) !== d.settings.daily_budget && edit({ op: "settings", daily_budget: Number(e.target.value) })} /> AUD/day</span>
              <span className="text-muted">Locations</span><span>{d.settings.locations.slice(0, 8).join(", ")}{d.settings.locations.length > 8 ? "…" : ""}</span>
            </div>
          </div>
          <div className="text-sm">
            <div className="font-medium">Launch checklist</div>
            <ul className="mt-1 grid gap-1 text-xs">
              {d.checklist.map((c) => <li key={c.key}><span className={`font-bold ${TONE[c.status]}`}>{ICON[c.status]}</span> {c.label} <span className="text-muted">— {c.detail}</span></li>)}
            </ul>
            <p className="mt-1 text-[11px] text-muted">Tracking may still fail at approval — the campaign stays paused; don&apos;t enable it until tracking passes.</p>
          </div>
        </div>
      </section>

      {!locked && (
        <section className={`${card} mb-4`}>
          <label className="text-sm font-medium">Approved USPs for the ads (one per line — Claude only claims these)
            <textarea className={`${input} mt-1 h-20 w-full text-xs`} value={usps} onChange={(e) => setUsps(e.target.value)}
              placeholder={"Fixed price airport transfers\nFlight tracking & free waiting\nMercedes-Benz fleet"} />
          </label>
        </section>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        {d.ad_groups.map((g) => (
          <section key={g.key} className={card}>
            <div className="flex items-center gap-2">
              <input className={`${input} flex-1 font-semibold`} defaultValue={g.name} disabled={locked}
                onBlur={(e) => e.target.value !== g.name && edit({ op: "rename_group", group: g.key, name: e.target.value })} />
              <span className="text-xs text-muted">{g.theme}</span>
            </div>
            <label className="mt-2 block text-xs text-muted">Landing page <span>(match {g.landing_score}/100 — {g.landing_reason})</span>
              <input className={`${input} mt-0.5 w-full text-xs`} defaultValue={g.final_url} disabled={locked}
                onBlur={(e) => e.target.value !== g.final_url && edit({ op: "set_url", group: g.key, url: e.target.value })} />
            </label>
            <div className="mt-2 text-xs font-medium">Keywords ({g.keywords.length}{g.reserve.length ? ` + ${g.reserve.length} low-volume held back` : ""})</div>
            <div className="mt-1 flex max-h-40 flex-wrap gap-1 overflow-y-auto">
              {g.keywords.map((k) => (
                <span key={k.text} className="inline-flex items-center gap-1 rounded-full border border-line px-2 py-0.5 text-xs" title={`${k.clicks} clicks · ${k.conversions} conv · AUD ${k.cost}`}>
                  {k.match_type === "EXACT" ? `[${k.text}]` : `"${k.text}"`}
                  {!locked && <>
                    <select aria-label={`Move ${k.text}`} className="bg-transparent text-muted" value="" onChange={(e) => e.target.value && edit({ op: "move_keyword", text: k.text, from: g.key, to: e.target.value })}>
                      <option value="">↪</option>
                      {groupKeys.filter((x) => x !== g.key).map((x) => <option key={x} value={x}>{d.ad_groups.find((y) => y.key === x)?.theme}</option>)}
                      <option value="unassigned">unassigned</option>
                    </select>
                    <button aria-label={`Remove ${k.text}`} className="text-muted hover:text-danger" onClick={() => edit({ op: "remove_keyword", text: k.text, from: g.key })}>×</button>
                  </>}
                </span>
              ))}
            </div>
            <div className="mt-3 rounded-md bg-surface-2 p-2 text-xs">
              {g.ad_draft_id ? (
                <>Ad: <b className={g.ad_status === "approved" ? "text-ok" : "text-warn"}>{g.ad_status}</b> · strength {g.ad_strength} · {g.ad_headlines.join(" | ")}
                  <div className="mt-1 flex gap-2"><Link href="/ads-assets" className="text-accent underline">Review / approve on Ads & Assets</Link>
                    {!locked && <button className="text-accent underline" disabled={!!busy} onClick={() => writeAds(g)}>Write again</button>}</div></>
              ) : !locked ? (
                <button className={btn} disabled={!!busy} onClick={() => writeAds(g)}>{busy === `ads-${g.key}` ? "Claude is writing…" : "✍ Write ads for this ad group"}</button>
              ) : "No ad"}
            </div>
          </section>
        ))}
      </div>

      {d.unassigned.length > 0 && (
        <section className={`${card} mt-3`}>
          <div className="text-sm font-medium">Not assigned to a theme ({d.unassigned.length}) — move the ones you want, the rest are left out</div>
          <div className="mt-2 flex flex-wrap gap-1">
            {d.unassigned.map((k) => (
              <span key={k.text} className="inline-flex items-center gap-1 rounded-full border border-dashed border-line px-2 py-0.5 text-xs">
                {k.text}
                {!locked && <select aria-label={`Move ${k.text}`} className="bg-transparent text-muted" value="" onChange={(e) => e.target.value && edit({ op: "move_keyword", text: k.text, from: "unassigned", to: e.target.value })}>
                  <option value="">↪</option>{d.ad_groups.map((g) => <option key={g.key} value={g.key}>{g.theme}</option>)}
                </select>}
              </span>
            ))}
          </div>
        </section>
      )}

      <section className={`${card} mt-3`}>
        <button className="text-sm font-medium" onClick={() => setShowNeg(!showNeg)}>{showNeg ? "▾" : "▸"} Campaign negative keywords ({d.negatives.length})</button>
        {showNeg && (
          <>
            {!locked && (
              <form className="mt-2 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (neg.trim()) { edit({ op: "add_negative", text: neg }); setNeg(""); } }}>
                <input className={input} value={neg} onChange={(e) => setNeg(e.target.value)} placeholder="add a negative, e.g. bus" /><button className={btn}>Add</button>
              </form>
            )}
            <ul className="mt-2 grid gap-0.5 text-xs md:grid-cols-2">
              {d.negatives.map((n) => (
                <li key={n.text}><span className="font-mono">&quot;{n.text}&quot;</span> <span className="text-muted">— {n.reason}</span>
                  {!locked && <button className="ml-1 text-muted hover:text-danger" onClick={() => edit({ op: "remove_negative", text: n.text })}>×</button>}</li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  );
}
