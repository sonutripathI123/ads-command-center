"use client";
// P13 — booking funnel: impressions → clicks → paid visits → leads (est.) → bookings → revenue, with bottlenecks.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Stage = { key: string; label: string; value: number | null; source: string; estimated: boolean; rate: number | null;
  cost_per: number | null; previous: number | null; change: number | null };
type Bottleneck = { code: string; severity: "critical" | "warning" | "info"; stage: string; title: string; detail: string; action: string; link: string | null };
type Camp = { google_id: string; name: string; status: string; clicks: number; cost: number; conversions: number; conversions_value: number;
  cost_per_conversion: number | null; roas_reported: number | null };
type Funnel = { website: { id: number; name: string; ads_account_id: number | null };
  period: { from: string; to: string; previous_from: string; previous_to: string }; stages: Stage[]; bottlenecks: Bottleneck[];
  ads_reported: { cost: number; conversions: number; conversions_value: number; cost_per_conversion: number | null } | null;
  ga4: { lead_events: string[]; first_day: string | null }; campaigns: Camp[];
  booking_quality: { channel: string; count: number; revenue: number; avg_value: number | null }[]; bookings_imported: boolean };
type Site = { id: number; name: string; domain: string; ads_account_id: number | null };

const BASE = `${API_BASE}/api/v1/funnel`;
async function call<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { credentials: "include" });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const SEV = { critical: "bg-danger/15 text-danger", warning: "bg-warn/15 text-warn", info: "bg-surface-2 text-muted" } as const;
const card = "rounded-lg border border-line bg-surface p-4";
const money = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `$${v.toLocaleString("en-AU", { maximumFractionDigits: 2 })}`);
const iso = (d: Date) => d.toISOString().slice(0, 10);
const ago = (n: number) => { const d = new Date(); d.setDate(d.getDate() - n); return iso(d); };
const PRESETS = [["30", "Last 30 days"], ["90", "Last 90 days"], ["custom", "Custom"]] as const;

function StageCard({ s }: { s: Stage }) {
  const v = s.value === null ? null : s.key === "revenue" ? money(s.value) : s.value.toLocaleString("en-AU");
  return (
    <div className={`rounded-md border p-3 ${s.value === null ? "border-dashed border-line" : "border-line bg-surface-2"}`}>
      <div className="text-xs text-muted">{s.label}</div>
      <div className={`text-xl font-semibold tabular-nums ${s.value === null ? "text-muted" : ""}`}>{v ?? "not measured"}{s.estimated && s.value !== null && <span className="ml-1 text-xs font-normal text-muted">est.</span>}</div>
      <div className="mt-1 text-[11px] text-muted">
        {s.rate !== null && <span className="mr-2">{(s.rate * 100).toFixed(1)}% of previous step</span>}
        {s.cost_per !== null && <span className="mr-2">{money(s.cost_per)} each</span>}
        {s.change !== null && <span className={s.change > 0 ? "text-ok" : s.change < 0 ? "text-danger" : ""}>{s.change > 0 ? "+" : ""}{(s.change * 100).toFixed(0)}% vs before</span>}
      </div>
      <div className="mt-1 text-[10px] text-muted">{s.source}</div>
    </div>
  );
}

export function FunnelPage() {
  const router = useRouter();
  const [sites, setSites] = useState<Site[] | null>(null);
  const [siteId, setSiteId] = useState<number | null>(null);
  const [preset, setPreset] = useState<string>("30");
  const [from, setFrom] = useState(ago(29));
  const [to, setTo] = useState(iso(new Date()));
  const [f, setF] = useState<Funnel | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    call<Site[]>("/websites").then((s) => { setSites(s); if (s[0]) setSiteId(s[0].id); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/bookings-revenue"); else setErr((e as Error).message); });
  }, [router]);

  const load = useCallback(async () => {
    if (!siteId) return;
    const [a, b] = preset === "custom" ? [from, to] : [ago(Number(preset) - 1), iso(new Date())];
    setF(await call<Funnel>(`/websites/${siteId}?date_from=${a}&date_to=${b}`));
    setErr(null);
  }, [siteId, preset, from, to]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on selection change
    load().catch((e) => setErr((e as Error).message));
  }, [load]);

  return (
    <>
      <PageHeader title="Bookings / Revenue" moduleId="P13">
        <div className="flex flex-wrap items-center gap-2">
          {sites && sites.length > 1 && (
            <select aria-label="Website" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={siteId ?? ""} onChange={(e) => setSiteId(Number(e.target.value))}>
              {sites.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          )}
          <select aria-label="Period" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={preset} onChange={(e) => setPreset(e.target.value)}>
            {PRESETS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
          {preset === "custom" && <>
            <input type="date" aria-label="From" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={from} onChange={(e) => setFrom(e.target.value)} />
            <input type="date" aria-label="To" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={to} onChange={(e) => setTo(e.target.value)} />
          </>}
        </div>
      </PageHeader>
      {err && <div role="status" className="mb-4 rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{err}</div>}
      {sites && !sites.length && <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">Add a website first.</p>}
      {f && <>
        <p className="mb-3 text-sm text-muted">
          How ad clicks turn into bookings for <b className="text-fg">{f.website.name}</b>, {f.period.from} → {f.period.to} (compared with {f.period.previous_from} → {f.period.previous_to}).
          Steps that can&apos;t be measured yet say so instead of showing zero.
        </p>
        <div className="mb-4 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">{f.stages.map((s) => <StageCard key={s.key} s={s} />)}</div>
        {f.bottlenecks.length > 0 && (
          <section className={`${card} mb-4`}>
            <h2 className="mb-2 font-semibold">Where the funnel leaks</h2>
            <ul className="grid gap-2">
              {f.bottlenecks.map((b) => (
                <li key={b.code} className="rounded-md bg-surface-2 p-3 text-sm">
                  <div className="flex flex-wrap items-start gap-2">
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${SEV[b.severity]}`}>{b.severity}</span>
                    <span className="flex-1 font-medium">{b.title}</span>
                    {b.link && <Link href={b.link} className="text-xs text-accent underline">Open →</Link>}
                  </div>
                  <p className="mt-1 text-xs text-muted">{b.detail}</p>
                  <p className="mt-1"><span className="text-xs text-muted">Do: </span>{b.action}</p>
                </li>
              ))}
            </ul>
          </section>
        )}
        <div className="grid gap-4 lg:grid-cols-2">
          <section className={card}>
            <h2 className="font-semibold">Campaigns (as reported by Google Ads)</h2>
            <p className="mb-2 text-xs text-muted">Conversions and value are Google Ads&apos; own numbers. Booking revenue per campaign needs per-booking data (pending change request).</p>
            {f.campaigns.length ? (
              <div className="overflow-x-auto"><table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-muted"><th className="py-1 pr-2">Campaign</th><th className="pr-2 text-right">Cost</th><th className="pr-2 text-right">Clicks</th><th className="pr-2 text-right">Conv.</th><th className="pr-2 text-right">Cost/conv.</th><th className="text-right">Value/cost</th></tr></thead>
                <tbody>{f.campaigns.map((c) => (
                  <tr key={c.google_id} className="border-t border-line"><td className="py-1 pr-2">{c.name} <span className="text-[10px] text-muted">{c.status.toLowerCase()}</span></td>
                    <td className="pr-2 text-right tabular-nums">{money(c.cost)}</td><td className="pr-2 text-right tabular-nums">{c.clicks}</td>
                    <td className="pr-2 text-right tabular-nums">{c.conversions}</td><td className="pr-2 text-right tabular-nums">{money(c.cost_per_conversion)}</td>
                    <td className="text-right tabular-nums">{c.roas_reported ?? "—"}</td></tr>))}</tbody>
              </table></div>
            ) : <p className="text-sm text-muted">{f.website.ads_account_id ? "No ad spend in this period." : "No Google Ads account linked to this website."}</p>}
          </section>
          <section className={card}>
            <h2 className="font-semibold">Booking quality by channel</h2>
            {f.booking_quality.length ? (
              <table className="mt-2 w-full text-sm">
                <thead><tr className="text-left text-xs text-muted"><th className="py-1">Channel</th><th className="text-right">Bookings</th><th className="text-right">Revenue</th><th className="text-right">Avg. value</th></tr></thead>
                <tbody>{f.booking_quality.map((q) => (
                  <tr key={q.channel} className="border-t border-line"><td className="py-1">{q.channel}</td><td className="text-right tabular-nums">{q.count}</td>
                    <td className="text-right tabular-nums">{money(q.revenue)}</td><td className="text-right tabular-nums">{money(q.avg_value)}</td></tr>))}</tbody>
              </table>
            ) : <p className="mt-2 text-sm text-muted">{f.bookings_imported ? "No bookings in this period." : <>No bookings imported yet — <Link href="/conversions" className="text-accent underline">import bookings</Link> to see revenue.</>}</p>}
            {f.ga4.lead_events.length > 0 && <p className="mt-3 text-xs text-muted">Lead events counted: {f.ga4.lead_events.join(", ")}</p>}
          </section>
        </div>
      </>}
    </>
  );
}
