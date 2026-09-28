"use client";
// P03 — one website: edit, scan, pages & issues, ad landing pages.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PageHeader } from "@/shell";
import { sitesApi, type CrawlRun, type LandingPage, type Meta, type PageRow, type Website } from "./api";
import { WebsiteForm } from "./WebsiteForm";

const card = "rounded-lg border border-line bg-surface p-4";
const LP_STATUS: Record<LandingPage["status"], { label: string; cls: string }> = {
  ok: { label: "OK", cls: "text-ok" }, broken: { label: "Broken", cls: "text-danger" },
  not_crawled: { label: "Not scanned", cls: "text-warn" }, other_domain: { label: "Other domain", cls: "text-muted" },
};

export function WebsiteDetail({ id }: { id: number }) {
  const router = useRouter();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [site, setSite] = useState<Website | null>(null);
  const [pages, setPages] = useState<PageRow[]>([]);
  const [lps, setLps] = useState<LandingPage[]>([]);
  const [run, setRun] = useState<CrawlRun | null>(null);
  const [tab, setTab] = useState<"issues" | "pages" | "landing">("issues");
  const [editing, setEditing] = useState(false);
  const [maxPages, setMaxPages] = useState(50);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, s, p, l] = await Promise.all([sitesApi.meta(), sitesApi.get(id), sitesApi.pages(id), sitesApi.landingPages(id)]);
      setMeta(m); setSite(s); setPages(p); setLps(l); setRun(s.last_crawl);
      return s.last_crawl;
    } catch (e) {
      if ((e as { status?: number }).status === 401) router.replace(`/login?next=/websites/${id}`);
      else setMsg({ ok: false, text: (e as Error).message });
      return null;
    }
  }, [id, router]);

  const watch = useCallback(() => {
    if (poll.current) clearInterval(poll.current);
    poll.current = setInterval(async () => {
      const [latest] = await sitesApi.crawls(id).catch(() => [null]);
      if (!latest) return;
      setRun(latest);
      if (latest.status !== "running" && poll.current) {
        clearInterval(poll.current);
        poll.current = null;
        await load();
        setMsg({ ok: latest.status !== "failed", text: `Scan ${latest.status}: ${latest.pages_crawled} page(s).` });
      }
    }, 2500);
  }, [id, load]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load
    load().then((last) => { if (last?.status === "running") watch(); });
    return () => { if (poll.current) clearInterval(poll.current); };
  }, [load, watch]);

  async function scan() {
    setMsg(null);
    try {
      setRun(await sitesApi.crawl(id, maxPages));
      watch();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  }

  const issueCounts = useMemo(() => {
    const c: Record<string, PageRow[]> = {};
    for (const p of pages) for (const i of p.issues) (c[i] ??= []).push(p);
    return Object.entries(c).sort((a, b) => b[1].length - a[1].length);
  }, [pages]);
  const labels = meta?.issue_labels ?? {};
  const path = (u: string) => { try { return new URL(u).pathname; } catch { return u; } };
  const running = run?.status === "running";

  if (!site || !meta) return msg ? <p className="text-sm text-danger">{msg.text}</p> : <p className="text-sm text-muted">Loading…</p>;
  return (
    <>
      <PageHeader title={site.name} moduleId="P03">
        <div className="flex flex-wrap items-center gap-2">
          <select aria-label="Pages to scan" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={maxPages} onChange={(e) => setMaxPages(Number(e.target.value))}>
            {[25, 50, 100, 200].map((n) => <option key={n} value={n}>up to {n} pages</option>)}
          </select>
          <button onClick={scan} disabled={running || !meta.crawler_enabled} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
            {running ? `Scanning… ${run?.pages_crawled ?? 0}` : "Scan website"}
          </button>
          <button onClick={() => setEditing(!editing)} className="rounded-md border border-line px-3 py-1.5 text-sm">Edit</button>
        </div>
      </PageHeader>
      <p className="-mt-3 mb-4 text-xs text-muted">
        <Link href="/websites" className="text-accent">← All websites</Link> · <a className="text-accent" href={site.base_url} target="_blank" rel="noreferrer">{site.domain}</a>
        {" "}· Google Ads {site.ads_customer_id ?? "not linked"} · GA4 {site.ga4_property_id ?? "—"}
        {run && ` · last scan ${new Date(run.started_at).toLocaleString("en-AU")} (${run.status}, ${run.source || "…"})`}
      </p>
      {!meta.crawler_enabled && (
        <div className="mb-4 rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn" role="status">
          Website scanning is switched off (feature flag <code>crawler.enabled</code>). Ask your admin to enable it.
        </div>
      )}
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      {editing && (
        <div className="mb-4">
          <WebsiteForm meta={meta} initial={site} onCancel={() => setEditing(false)} onSave={async (w) => {
            const { domain: _d, ...rest } = w; // eslint-disable-line @typescript-eslint/no-unused-vars
            setSite(await sitesApi.update(id, rest));
            setEditing(false);
          }} />
        </div>
      )}

      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        {[["Pages scanned", pages.length], ["Pages with issues", pages.filter((p) => p.issues.length).length],
          ["Ad landing pages", lps.length], ["Landing pages with problems", lps.filter((l) => l.status === "broken" || l.status === "not_crawled").length]]
          .map(([l, v]) => <div key={String(l)} className={card}><div className="text-sm text-muted">{l}</div><div className="mt-1 text-2xl font-semibold tabular-nums">{v}</div></div>)}
      </div>

      <div role="tablist" className="mb-3 flex w-fit overflow-hidden rounded-md border border-line">
        {([["issues", "Issues"], ["pages", "All pages"], ["landing", "Ad landing pages"]] as const).map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`px-3 py-1 text-sm ${tab === k ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"}`}>{l}</button>
        ))}
      </div>

      {tab === "issues" && (
        <section className={card}>
          {!pages.length ? <p className="text-sm text-muted">Not scanned yet. Click “Scan website”.</p> : !issueCounts.length ? <p className="text-sm text-ok">No issues found 🎉</p> : (
            <ul className="divide-y divide-line">
              {issueCounts.map(([code, ps]) => (
                <li key={code} className="py-2">
                  <details>
                    <summary className="cursor-pointer text-sm"><b>{labels[code] ?? code}</b> <span className="text-muted">— {ps.length} page(s)</span></summary>
                    <ul className="mt-1 list-disc pl-6 text-xs text-muted">{ps.map((p) => <li key={p.id}><a className="text-accent" href={p.url} target="_blank" rel="noreferrer">{path(p.url)}</a> {p.title && `— ${p.title}`}</li>)}</ul>
                  </details>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === "pages" && (
        <section className={`${card} overflow-x-auto`}>
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted"><tr>
              <th className="py-1 pr-3 font-medium">Page</th><th className="pr-3 font-medium">Title / H1</th><th className="pr-3 text-right font-medium">Words</th>
              <th className="pr-3 font-medium">Book/quote</th><th className="pr-3 font-medium">Form</th><th className="pr-3 font-medium">Phone</th>
              <th className="pr-3 font-medium">Services found</th><th className="pr-3 text-right font-medium">Speed</th><th className="font-medium">Issues</th></tr></thead>
            <tbody className="divide-y divide-line">
              {pages.map((p) => (
                <tr key={p.id} className="align-top">
                  <td className="py-1.5 pr-3 text-xs"><a className="text-accent" href={p.url} target="_blank" rel="noreferrer">{path(p.url)}</a>{p.status_code !== 200 && <span className="ml-1 text-danger">{p.status_code ?? "error"}</span>}</td>
                  <td className="max-w-xs pr-3 text-xs">{p.title}<div className="text-muted">{p.h1}</div></td>
                  <td className="pr-3 text-right tabular-nums">{p.word_count}</td>
                  <td className="pr-3">{p.cta_count ? "✓" : <span className="text-danger">✗</span>}</td>
                  <td className="pr-3">{p.has_form ? "✓" : "—"}</td>
                  <td className="pr-3">{p.has_phone ? "✓" : "—"}</td>
                  <td className="max-w-[12rem] pr-3 text-xs text-muted">{p.services.slice(0, 4).join(", ") || "—"}</td>
                  <td className={`pr-3 text-right tabular-nums ${p.response_ms && p.response_ms > 3000 ? "text-danger" : ""}`}>{p.response_ms ? `${(p.response_ms / 1000).toFixed(1)}s` : "—"}</td>
                  <td className="text-xs">{p.issues.length ? p.issues.map((i) => labels[i] ?? i).join("; ") : <span className="text-ok">none</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {tab === "landing" && (
        <section className={`${card} overflow-x-auto`}>
          <div className="mb-2 flex items-center gap-2 text-sm text-muted">
            Final URLs of this site’s ads (last 90 days, from the linked Google Ads account).
            <button className="ml-auto rounded-md border border-line px-2.5 py-1 text-sm" onClick={async () => { await sitesApi.refreshLanding(id); await load(); }}>Refresh</button>
          </div>
          {!site.ads_account_id ? <p className="text-sm text-muted">Link a Google Ads account (Edit) to see ad landing pages.</p> : !lps.length ? <p className="text-sm text-muted">No ads found — sync the account on the Campaigns page, then scan.</p> : (
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-muted"><tr><th className="py-1 pr-3 font-medium">Landing page</th><th className="pr-3 font-medium">Status</th><th className="pr-3 text-right font-medium">Ads</th><th className="pr-3 font-medium">Used by</th><th className="font-medium">Page issues</th></tr></thead>
              <tbody className="divide-y divide-line">
                {lps.map((l) => (
                  <tr key={l.final_url} className="align-top">
                    <td className="py-1.5 pr-3 text-xs"><a className="text-accent" href={l.final_url} target="_blank" rel="noreferrer">{l.final_url}</a>{l.title && <div className="text-muted">{l.title}</div>}</td>
                    <td className={`pr-3 text-xs font-medium ${LP_STATUS[l.status].cls}`}>{LP_STATUS[l.status].label}</td>
                    <td className="pr-3 text-right tabular-nums">{l.ads}</td>
                    <td className="max-w-xs pr-3 text-xs text-muted">{l.ad_groups.slice(0, 3).join("; ")}{l.ad_groups.length > 3 ? ` +${l.ad_groups.length - 3}` : ""}</td>
                    <td className="text-xs">{l.issues.map((i) => labels[i] ?? i).join("; ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </>
  );
}
