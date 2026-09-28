"use client";
// P06 — tracking health, GA4 traffic & events (with lead/booking roles), organic queries, bookings import.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, SCOPE_ALL, useScope } from "@/shell";
import { convApi, type Health, type ImportResult, type Overview, type SiteRow, type SyncRun } from "./api";

const card = "rounded-lg border border-line bg-surface p-4";
const RANGES = [7, 30, 90];
const ROLES = [["", "— not set —"], ["lead", "Lead (enquiry / quote / call)"], ["booking", "Booking"], ["micro", "Micro step"], ["ignore", "Ignore"]];
const SEV = {
  critical: "border-danger/30 bg-danger/10 text-danger", warning: "border-warn/30 bg-warn/10 text-warn", info: "border-line bg-surface-2 text-muted",
} as const;
const nf = (n: number, d = 0) => new Intl.NumberFormat("en-AU", { maximumFractionDigits: d }).format(n);
const money = (n: number) => new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD" }).format(n);


type TabKey = "ga4" | "gsc" | "bookings";
const TABS: { key: TabKey; icon: string; label: string; sub: string }[] = [
  { key: "ga4", icon: "📊", label: "Google Analytics (GA4)", sub: "what visitors do on your site" },
  { key: "gsc", icon: "🔍", label: "Search Console", sub: "free Google search results" },
  { key: "bookings", icon: "📅", label: "Bookings", sub: "real confirmed jobs" },
];
const tabOf = (code: string): TabKey => (code === "no_gsc" ? "gsc" : code === "no_bookings" ? "bookings" : "ga4");
const EVENT_HELP: Record<string, string> = {
  page_view: "a page was opened", session_start: "a visit started", first_visit: "first-ever visit", user_engagement: "stayed on the page",
  scroll: "scrolled to the bottom", form_start: "started filling a form (not sent)", form_submit: "sent a form", generate_lead: "enquiry sent",
  click: "clicked an outbound link", file_download: "downloaded a file",
};

function Explain({ children }: { children: React.ReactNode }) {
  return <p className="mb-4 rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-muted">{children}</p>;
}

function Tile({ label, value, note, warn }: { label: string; value: string; note?: string; warn?: boolean }) {
  return (
    <div className={`${card} ${warn ? "border-danger/40" : ""}`}>
      <div className="text-sm text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${warn ? "text-danger" : ""}`}>{value}</div>
      {note && <div className="mt-1 text-xs text-muted">{note}</div>}
    </div>
  );
}

function HealthList({ items }: { items: Health[] }) {
  if (!items.length) return null;
  return (
    <section className="mb-4 grid gap-2">
      {items.map((h) => (
        <div key={h.code} className={`rounded-md border px-3 py-2 text-sm ${SEV[h.severity]}`}>
          <b>{h.severity === "critical" ? "✖" : h.severity === "warning" ? "⚠" : "ℹ"} {h.title}</b>
          <div className="mt-0.5 text-fg/80">{h.detail}</div>
        </div>
      ))}
    </section>
  );
}

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
  const [tab, setTab] = useState<TabKey>("ga4");
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
          <div role="tablist" aria-label="Data source" className="mb-4 flex flex-wrap gap-2">
            {TABS.map((tb) => {
              const n = ov.health.filter((h) => tabOf(h.code) === tb.key && h.severity !== "info").length;
              return (
                <button key={tb.key} role="tab" aria-selected={tab === tb.key} onClick={() => setTab(tb.key)}
                  className={`rounded-lg border px-4 py-2 text-left text-sm ${tab === tb.key ? "border-accent bg-accent-soft" : "border-line bg-surface hover:bg-surface-2"}`}>
                  <div className="font-semibold">{tb.icon} {tb.label}</div>
                  <div className="text-xs text-muted">{tb.sub}{n > 0 && <span className="ml-1 text-danger">· {n} problem{n > 1 ? "s" : ""}</span>}</div>
                </button>
              );
            })}
          </div>

          <HealthList items={ov.health.filter((h) => tabOf(h.code) === tab)} />

          {tab === "ga4" && (
            <>
              <Explain>
                <b>Google Analytics (GA4)</b> tells you what people do <b>on your website</b> after they arrive — from ads, Google search,
                direct visits, social… It is the only place that can show enquiries (form submits) and bookings as they happen.
                {ov.ga4_first_day && <> Data for this site starts on <b>{ov.ga4_first_day}</b>.</>}
              </Explain>
              <div className="mb-4 grid gap-3 sm:grid-cols-3">
                <Tile label="Visits (sessions)" value={nf(ov.totals.sessions)} note="all channels" />
                <Tile label="Engaged visits" value={nf(ov.totals.engaged_sessions)}
                  note={ov.totals.sessions ? `${Math.round((ov.totals.engaged_sessions / ov.totals.sessions) * 100)}% stayed 10 s+ or viewed 2+ pages` : undefined} />
                <Tile label="Conversions (key events)" value={nf(ov.totals.key_events, 1)} note={ov.totals.key_events ? "enquiries / bookings recorded" : "nothing is being recorded"} warn={!ov.totals.key_events} />
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <section className={card}>
                  <h2 className="mb-1 font-semibold">Where visitors come from</h2>
                  <p className="mb-2 text-xs text-muted">“Paid Search” = your Google Ads. “Organic Search” = free Google results (details in the Search Console tab).</p>
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs text-muted"><tr><th className="py-1 font-medium">Channel</th><th className="text-right font-medium">Visits</th><th className="text-right font-medium">Engaged</th><th className="text-right font-medium">Conversions</th></tr></thead>
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
                  <h2 className="mb-1 font-semibold">What visitors did (GA4 events)</h2>
                  <p className="mb-2 text-xs text-muted">Tell the system what each event means. Mark the one sent when an enquiry or booking is <b>completed</b> as “Lead” or “Booking”.</p>
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs text-muted"><tr><th className="py-1 font-medium">Event</th><th className="text-right font-medium">Count</th><th className="text-right font-medium">Key?</th><th className="pl-3 font-medium">Means</th></tr></thead>
                    <tbody className="divide-y divide-line">
                      {ov.events.map((e) => (
                        <tr key={e.event_name}>
                          <td className="py-1.5 font-mono text-xs">{e.event_name}<div className="font-sans text-muted">{EVENT_HELP[e.event_name] ?? ""}</div></td>
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
              </div>
            </>
          )}

          {tab === "gsc" && (
            <>
              <Explain>
                <b>Google Search Console</b> shows how your site appears in the <b>free (organic) Google results</b> — before anyone
                clicks. No ad money is involved. Use it to see which searches find you for free and where you rank.
              </Explain>
              {(() => {
                const top = ov.top_queries;
                const impr = top.reduce((s, q) => s + q.impressions, 0);
                const pos = impr ? top.reduce((s, q) => s + q.position * q.impressions, 0) / impr : 0;
                const { clicks, impressions } = ov.organic_totals;
                return (
                  <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <Tile label="Clicks from Google search" value={nf(clicks)} note="free visits" />
                    <Tile label="Times shown in Google" value={nf(impressions)} note="impressions" />
                    <Tile label="Click rate" value={impressions ? `${((clicks / impressions) * 100).toFixed(1)}%` : "—"} note="clicks ÷ impressions" />
                    <Tile label="Average position" value={pos ? pos.toFixed(1) : "—"} note="1–10 = first page" warn={pos > 10} />
                  </div>
                );
              })()}
              <section className={card}>
                <h2 className="mb-1 font-semibold">Searches that show your site</h2>
                <p className="mb-2 text-xs text-muted">Position above 10 (amber) means you are on page 2 or lower for that search.</p>
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-muted"><tr><th className="py-1 font-medium">Search</th><th className="text-right font-medium">Clicks</th><th className="text-right font-medium">Shown</th><th className="text-right font-medium">Click rate</th><th className="text-right font-medium">Avg position</th></tr></thead>
                  <tbody className="divide-y divide-line">
                    {ov.top_queries.slice(0, 50).map((q) => (
                      <tr key={q.query}><td className="py-1.5">{q.query}</td><td className="text-right tabular-nums">{q.clicks}</td>
                        <td className="text-right tabular-nums">{nf(q.impressions)}</td>
                        <td className="text-right tabular-nums">{q.impressions ? `${((q.clicks / q.impressions) * 100).toFixed(1)}%` : "—"}</td>
                        <td className={`text-right tabular-nums ${q.position > 10 ? "text-warn" : ""}`}>{q.position}</td></tr>
                    ))}
                  </tbody>
                </table>
                {!ov.top_queries.length && <p className="text-sm text-muted">No Search Console data — link the property on the Websites page and Sync.</p>}
              </section>
            </>
          )}

          {tab === "bookings" && (
            <>
              <Explain>
                <b>Bookings</b> are the real, confirmed jobs from your booking system — the number that matters most.
                Upload a CSV export; later this comes live from the Driver App.
              </Explain>
              <div className="mb-4 grid gap-3 sm:grid-cols-3">
                <Tile label="Confirmed bookings" value={nf(ov.bookings.count)} />
                <Tile label="Revenue" value={money(ov.bookings.revenue)} />
                <Tile label="From Google Ads" value={`${ov.bookings.google_ads.count} · ${money(ov.bookings.google_ads.revenue)}`} note="gclid / UTM google-cpc" />
              </div>
              <section className={card}>
                <p className="mb-2 text-xs text-muted">
                  Required columns: booking id, date booked, amount. Optional: pickup date, status, service, website, channel, gclid,
                  utm_source/medium/campaign. Names, emails and phone numbers are <b>ignored</b>.
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
            </>
          )}
        </>
      )}
    </>
  );
}
