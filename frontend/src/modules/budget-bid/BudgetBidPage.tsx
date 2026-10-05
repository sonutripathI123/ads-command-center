"use client";
// P12 — where and when the Google Ads money works: device, weekday, time of day, location, budget. Advice only.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Row = { key: string; label?: string; canonical?: string; type?: string; impressions: number; clicks: number; cost: number; conversions: number };
type Camp = { campaign: string; status: string; bidding: string; daily_budget: number; cost: number; conversions: number; impression_share: number | null;
  lost_budget: number | null; lost_rank: number | null };
type Finding = { id: number; dimension: string; segment: string; severity: "warning" | "info"; title: string; observation: string; evidence: [string, string][];
  proposed_action: string; confidence: "low" | "medium" };
type Snap = { run: { id: number; days: number; date_from: string; date_to: string; created_at: string } | null; findings: Finding[];
  total?: { cost: number; clicks: number; conversions: number }; average_cpa?: number | null;
  tables: { device: Row[]; day: Row[]; daypart: Row[]; location: Row[]; campaigns: Camp[] } | null };
type Account = { id: number; customer_id: string; name: string };

const BASE = `${API_BASE}/api/v1/budget-bid`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const SEV = { warning: "bg-warn/15 text-warn", info: "bg-surface-2 text-muted" } as const;
const money = (v: number) => `$${v.toLocaleString("en-AU", { maximumFractionDigits: 0 })}`;
const pct = (v: number | null) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);
const NAMES: Record<string, string> = { MOBILE: "Mobile", DESKTOP: "Desktop", TABLET: "Tablet", CONNECTED_TV: "Connected TV", OTHER: "Other" };
const nice = (s: string) => NAMES[s] ?? (s === s.toUpperCase() && s.length > 3 ? s[0] + s.slice(1).toLowerCase() : s);

function SegTable({ title, rows, name }: { title: string; rows: Row[]; name?: (r: Row) => string }) {
  const max = Math.max(1, ...rows.map((r) => r.cost));
  return (
    <section className="rounded-lg border border-line bg-surface p-4">
      <h2 className="mb-2 font-semibold">{title}</h2>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs text-muted"><th className="py-1">Segment</th><th className="text-right">Spend</th><th className="text-right">Clicks</th>
          <th className="text-right">Conv.</th><th className="text-right">Cost / conv.</th><th className="w-24 pl-3" /></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="border-t border-line">
              <td className="py-1">{name ? name(r) : nice(r.key)}</td>
              <td className="text-right tabular-nums">{money(r.cost)}</td><td className="text-right tabular-nums">{r.clicks}</td>
              <td className="text-right tabular-nums">{r.conversions.toFixed(1)}</td>
              <td className="text-right tabular-nums">{r.conversions > 0 ? money(r.cost / r.conversions) : "—"}</td>
              <td className="pl-3"><div className="h-1.5 rounded bg-accent/60" style={{ width: `${(r.cost / max) * 100}%` }} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function BudgetBidPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accId, setAccId] = useState<number | null>(null);
  const [snap, setSnap] = useState<Snap | null>(null);
  const [days, setDays] = useState(90);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    call<Account[]>("/accounts").then((a) => { setAccounts(a); if (a[0]) setAccId(a[0].id); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/budget-bid"); else setMsg({ ok: false, text: (e as Error).message }); });
  }, [router]);

  const load = useCallback(async () => { if (accId) setSnap(await call<Snap>(`/accounts/${accId}/latest`)); }, [accId]);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on account change
    load().catch((e) => setMsg({ ok: false, text: (e as Error).message }));
  }, [load]);

  async function runNow() {
    setBusy(true); setMsg(null);
    try { setSnap(await call<Snap>(`/accounts/${accId}/run`, { method: "POST", body: JSON.stringify({ days }) })); setMsg({ ok: true, text: "Analysis updated from Google Ads." }); }
    catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(false); }
  }

  const t = snap?.tables;
  return (
    <>
      <PageHeader title="Budget & Bid Insights" moduleId="P12">
        <div className="flex flex-wrap items-center gap-2">
          {accounts.length > 1 && (
            <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => setAccId(Number(e.target.value))}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
            </select>
          )}
          <select aria-label="Period" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[30, 60, 90, 180].map((d) => <option key={d} value={d}>Last {d} days</option>)}
          </select>
          <button onClick={runNow} disabled={!accId || busy} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">{busy ? "Reading Google Ads…" : "Run analysis"}</button>
        </div>
      </PageHeader>
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      <p className="mb-4 text-sm text-muted">
        Which device, day, time of day and place bring bookings — and which only cost money — plus whether each campaign is limited by budget or by ad rank.
        Advice only: nothing is changed in Google Ads. With few conversions most differences are within chance, so each point shows its confidence.
        Related: <Link href="/monitoring" className="text-accent underline">Monitoring</Link> · <Link href="/search-terms/negatives" className="text-accent underline">Negative keywords</Link>.
      </p>
      {snap && !snap.run && <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">No analysis yet. Click <b>Run analysis</b> (reads Google Ads, takes a few seconds).</p>}
      {snap?.run && t && (
        <>
          <p className="mb-3 text-xs text-muted">
            {snap.run.date_from} → {snap.run.date_to} · {money(snap.total?.cost ?? 0)} spent · {snap.total?.clicks} clicks · {snap.total?.conversions.toFixed(1)} conversions
            {snap.average_cpa ? ` · average ${money(snap.average_cpa)} per conversion` : ""} · analysed {new Date(snap.run.created_at).toLocaleString("en-AU")}
          </p>
          <section className="mb-4 rounded-lg border border-line bg-surface p-4">
            <h2 className="mb-2 font-semibold">What stands out</h2>
            {!snap.findings.length ? <p className="text-sm text-muted">Nothing stands out beyond normal variation.</p> : (
              <ul className="grid gap-2">
                {snap.findings.map((f) => (
                  <li key={f.id} className="rounded-md bg-surface-2 p-3 text-sm">
                    <div className="flex flex-wrap items-start gap-2">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${SEV[f.severity]}`}>{f.severity}</span>
                      <span className="flex-1 font-medium">{f.title}</span>
                      <span className="text-[10px] uppercase text-muted">{f.dimension} · {f.confidence} confidence</span>
                    </div>
                    <p className="mt-1 text-xs text-muted">{f.observation}</p>
                    {f.evidence.length > 0 && (
                      <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 text-xs">
                        {f.evidence.map(([k, v], i) => <Fragment key={i}><dt className="text-muted">{k}</dt><dd>{v}</dd></Fragment>)}
                      </dl>
                    )}
                    <p className="mt-1"><span className="text-xs text-muted">Do: </span>{f.proposed_action}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <div className="grid gap-4 lg:grid-cols-2">
            <SegTable title="By device" rows={t.device} />
            <SegTable title="By day of week" rows={t.day} />
            <SegTable title="By time of day" rows={t.daypart} name={(r) => r.key} />
            <SegTable title="Top places (by spend)" rows={t.location.slice(0, 15)} name={(r) => `${r.label ?? r.key}${r.type ? ` (${r.type.toLowerCase()})` : ""}`} />
          </div>
          <section className="mt-4 rounded-lg border border-line bg-surface p-4">
            <h2 className="mb-2 font-semibold">Campaign budget &amp; ad rank</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-muted"><th className="py-1">Campaign</th><th>Status</th><th className="text-right">Daily budget</th><th className="text-right">Spend</th>
                  <th className="text-right">Conv.</th><th className="text-right">Impr. share</th><th className="text-right">Lost: budget</th><th className="text-right">Lost: ad rank</th><th className="pl-3">Bidding</th></tr></thead>
                <tbody>
                  {t.campaigns.map((c) => (
                    <tr key={c.campaign} className="border-t border-line">
                      <td className="py-1">{c.campaign}</td><td>{c.status.toLowerCase()}</td><td className="text-right tabular-nums">${c.daily_budget.toFixed(2)}</td>
                      <td className="text-right tabular-nums">{money(c.cost)}</td><td className="text-right tabular-nums">{c.conversions.toFixed(1)}</td>
                      <td className="text-right tabular-nums">{pct(c.impression_share)}</td><td className="text-right tabular-nums">{pct(c.lost_budget)}</td>
                      <td className="text-right tabular-nums">{pct(c.lost_rank)}</td><td className="pl-3 text-xs">{c.bidding.toLowerCase().replaceAll("_", " ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}
