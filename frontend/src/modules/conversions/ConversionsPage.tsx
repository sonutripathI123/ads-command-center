"use client";
// P06 — tracking health, GA4 traffic & events (with lead/booking roles), organic queries, bookings import.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, SCOPE_ALL, useScope } from "@/shell";
import { convApi, type ImportResult, type Overview, type SiteRow, type SyncRun } from "./api";

const card = "rounded-lg border border-line bg-surface p-4";
const RANGES = [7, 30, 90];
const ROLES = [["", "— not set —"], ["lead", "Lead (enquiry / quote / call)"], ["booking", "Booking"], ["micro", "Micro step"], ["ignore", "Ignore"]];
const SEV = {
  critical: "border-danger/30 bg-danger/10 text-danger", warning: "border-warn/30 bg-warn/10 text-warn", info: "border-line bg-surface-2 text-muted",
} as const;
const nf = (n: number, d = 0) => new Intl.NumberFormat("en-AU", { maximumFractionDigits: d }).format(n);
const money = (n: number) => new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD" }).format(n);

export function ConversionsPage() {
  const router = useRouter();
  const scope = useScope();
  const [sites, setSites] = useState<SiteRow[] | null>(null);
  const [siteId, setSiteId] = useState<number | null>(null);
  const [days, setDays] = useState(30);
  const [ov, setOv] = useState<Overview | null>(null);
  const [run, setRun] = useState<SyncRun | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [imp, setImp] = useState<ImportResult | null>(null);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    convApi.websites().then((s) => {
      setSites(s);
      const fromScope = scope.websiteId !== SCOPE_ALL ? s.find((x) => String(x.id) === scope.websiteId) : undefined;
      const pick = fromScope ?? s[0];
      if (pick) { setSiteId(pick.id); setRun(pick.last_run); }
    }).catch((e) => {
      if ((e as { status?: number }).status === 401) router.replace("/login?next=/conversions");
      else setMsg({ ok: false, text: (e as Error).message });
    });
    return () => { if (poll.current) clearInterval(poll.current); };
  }, [router, scope.websiteId]);

  const load = useCallback(async () => {
    if (!siteId) return;
    try {
      setOv(await convApi.overview(siteId, days));
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  }, [siteId, days]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on selection change
    load();
  }, [load]);

  async function sync() {
    if (!siteId) return;
    setMsg(null);
    try {
      setRun(await convApi.sync(siteId, 90));
      if (poll.current) clearInterval(poll.current);
      poll.current = setInterval(async () => {
        const [r] = await convApi.runs(siteId).catch(() => [null]);
        if (!r) return;
        setRun(r);
        if (r.status !== "running" && poll.current) {
          clearInterval(poll.current);
          poll.current = null;
          setMsg({ ok: r.status !== "failed", text: `Sync ${r.status}${Object.keys(r.errors).length ? ": " + Object.values(r.errors).join("; ") : ""}` });
          await load();
        }
      }, 2000);
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  }

  async function setRole(event: string, role: string) {
    if (!siteId || !role) return;
    try {
      await convApi.setRole(siteId, event, role);
      await load();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  }

  async function upload(file: File) {
    setMsg(null);
    try {
      const r = await convApi.importBookings(await file.text(), siteId);
      setImp(r);
      await load();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  }

  const site = sites?.find((s) => s.id === siteId);
  const btn = "rounded-md border border-line px-2.5 py-1 text-sm hover:bg-surface-2 disabled:opacity-50";

  return (
    <>
      <PageHeader title="Conversions & Analytics" moduleId="P06">
        <div className="flex flex-wrap items-center gap-2">
          {sites && sites.length > 1 && (
            <select aria-label="Website" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={siteId ?? ""}
              onChange={(e) => { const s = sites.find((x) => x.id === Number(e.target.value)); setSiteId(s?.id ?? null); setRun(s?.last_run ?? null); }}>
              {sites.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          )}
          <div role="group" aria-label="Date range" className="flex overflow-hidden rounded-md border border-line">
            {RANGES.map((d) => (
              <button key={d} aria-pressed={days === d} onClick={() => setDays(d)}
                className={`px-2.5 py-1 text-sm ${days === d ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"}`}>{d}d</button>
            ))}
          </div>
          <button className={btn} onClick={sync} disabled={!siteId || run?.status === "running"}>{run?.status === "running" ? "Syncing…" : "Sync GA4 & Search Console"}</button>
        </div>
      </PageHeader>
      {site && (
        <p className="-mt-3 mb-4 text-xs text-muted">
          {site.domain} · GA4 {site.ga4_property_id ?? "not linked"} · Search Console {site.gsc_site_url ? "linked" : "not linked"} ·
          {" "}last sync {run ? `${new Date(run.started_at).toLocaleString("en-AU")} (${run.status})` : "never"}
        </p>
      )}
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      {sites && !sites.length && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">
          Add a website with its GA4 property on the <Link className="text-accent underline" href="/websites">Websites</Link> page first.
        </p>
      )}

      {ov && (
        <>
          {ov.health.length > 0 && (
            <section className="mb-4 grid gap-2">
              <h2 className="font-semibold">Tracking health</h2>
              {ov.health.map((h) => (
                <div key={h.code} className={`rounded-md border px-3 py-2 text-sm ${SEV[h.severity]}`}>
                  <b>{h.severity === "critical" ? "✖" : h.severity === "warning" ? "⚠" : "ℹ"} {h.title}</b>
                  <div className="mt-0.5 text-fg/80">{h.detail}</div>
                </div>
              ))}
            </section>
          )}

          <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {[["Sessions (GA4)", nf(ov.totals.sessions)], ["Engaged sessions", nf(ov.totals.engaged_sessions)],
              ["Key events (GA4)", nf(ov.totals.key_events, 1)], ["Organic clicks (Search Console)", nf(ov.organic_totals.clicks)],
              ["Confirmed bookings", `${ov.bookings.count} · ${money(ov.bookings.revenue)}`]].map(([l, v]) => (
              <div key={l} className={card}><div className="text-sm text-muted">{l}</div><div className="mt-1 text-2xl font-semibold tabular-nums">{v}</div></div>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className={card}>
              <h2 className="mb-2 font-semibold">Traffic by channel (GA4)</h2>
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-muted"><tr><th className="py-1 font-medium">Channel</th><th className="text-right font-medium">Sessions</th><th className="text-right font-medium">Engaged</th><th className="text-right font-medium">Key events</th></tr></thead>
                <tbody className="divide-y divide-line">
                  {ov.channels.map((c) => (
                    <tr key={c.channel}><td className="py-1.5">{c.channel}</td><td className="text-right tabular-nums">{nf(c.sessions)}</td>
                      <td className="text-right tabular-nums">{nf(c.engaged_sessions)}</td><td className="text-right tabular-nums">{nf(c.key_events, 1)}</td></tr>
                  ))}
                </tbody>
              </table>
              {!ov.channels.length && <p className="text-sm text-muted">No GA4 data for this period — click Sync.</p>}
            </section>

            <section className={card}>
              <h2 className="mb-1 font-semibold">GA4 events — what does each mean?</h2>
              <p className="mb-2 text-xs text-muted">Mark the event(s) fired when someone sends an enquiry or books. Reports count leads from these.</p>
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-muted"><tr><th className="py-1 font-medium">Event</th><th className="text-right font-medium">Count</th><th className="text-right font-medium">Key?</th><th className="pl-3 font-medium">Means</th></tr></thead>
                <tbody className="divide-y divide-line">
                  {ov.events.map((e) => (
                    <tr key={e.event_name}>
                      <td className="py-1.5 font-mono text-xs">{e.event_name}</td>
                      <td className="text-right tabular-nums">{nf(e.event_count)}</td>
                      <td className="text-right">{e.key_events > 0 ? "✓" : "—"}</td>
                      <td className="pl-3">
                        <select aria-label={`Role of ${e.event_name}`} className="rounded-md border border-line bg-surface px-1.5 py-0.5 text-xs" value={e.role ?? ""}
                          onChange={(ev) => setRole(e.event_name, ev.target.value)}>
                          {ROLES.map(([v, l]) => <option key={v} value={v}>{l}{!e.role && v === e.suggested_role ? " (suggested)" : ""}</option>)}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className={card}>
              <h2 className="mb-2 font-semibold">Top organic searches (Search Console)</h2>
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-muted"><tr><th className="py-1 font-medium">Search</th><th className="text-right font-medium">Clicks</th><th className="text-right font-medium">Impr.</th><th className="text-right font-medium">Avg pos.</th></tr></thead>
                <tbody className="divide-y divide-line">
                  {ov.top_queries.slice(0, 25).map((q) => (
                    <tr key={q.query}><td className="py-1.5">{q.query}</td><td className="text-right tabular-nums">{q.clicks}</td>
                      <td className="text-right tabular-nums">{nf(q.impressions)}</td><td className={`text-right tabular-nums ${q.position > 10 ? "text-warn" : ""}`}>{q.position}</td></tr>
                  ))}
                </tbody>
              </table>
              {!ov.top_queries.length && <p className="text-sm text-muted">No Search Console data — link the property on the Websites page and Sync.</p>}
            </section>

            <section className={card}>
              <h2 className="mb-1 font-semibold">Confirmed bookings</h2>
              <p className="mb-2 text-xs text-muted">
                Upload a CSV export from your booking system. Required columns: booking id, date booked, amount. Optional: pickup date, status,
                service, website, channel, gclid, utm_source/medium/campaign. Names, emails and phone numbers are <b>ignored</b>.
              </p>
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-line px-2.5 py-1 text-sm hover:bg-surface-2">
                Upload bookings CSV
                <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
              </label>
              {imp && (
                <p className="mt-2 text-sm">
                  {imp.created} new · {imp.updated} updated · {imp.skipped} skipped
                  {imp.errors.length > 0 && <span className="text-danger"> — {imp.errors.slice(0, 3).join("; ")}</span>}
                  {imp.ignored_columns.length > 0 && <span className="text-muted"> · ignored columns: {imp.ignored_columns.join(", ")}</span>}
                </p>
              )}
              {ov.bookings.count > 0 && (
                <table className="mt-3 w-full text-left text-sm">
                  <thead className="text-xs text-muted"><tr><th className="py-1 font-medium">Channel</th><th className="text-right font-medium">Bookings</th><th className="text-right font-medium">Revenue</th></tr></thead>
                  <tbody className="divide-y divide-line">
                    {ov.bookings.by_channel.map((c) => <tr key={c.channel}><td className="py-1.5">{c.channel}</td><td className="text-right tabular-nums">{c.count}</td><td className="text-right tabular-nums">{money(c.revenue)}</td></tr>)}
                  </tbody>
                </table>
              )}
            </section>
          </div>
          <p className="mt-4 text-xs text-muted">
            Observed = GA4/Search Console · Attributed = Google Ads conversions (Campaigns page) · Confirmed = bookings. Kept separate on purpose.
          </p>
        </>
      )}
    </>
  );
}
