"use client";
// P10 — ad landing pages: CRO findings (intent, CTA, form, trust, mobile, speed, tracking) and implementation briefs.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Finding = { code: string; category: string; severity: "critical" | "warning" | "info"; title: string; detail: string;
  recommendation: string; evidence: [string, string][] };
type Check = { id: number; run_key: string; url: string; final_url: string | null; status_code: number | null; elapsed_ms: number | null;
  error: string | null; score: number; checked_at: string; checked_by: string | null; ads: number; ad_groups: string[]; cost: number;
  clicks: number; conversions: number; counts: Record<string, number>; findings: Finding[]; latest_brief_id: number | null };
type Run = { run_key: string; checked_at: string; pages: number; avg_score: number };
type Account = { id: number; customer_id: string; name: string; landing_urls: number; runs: Run[] };
type Meta = { fetch_enabled: boolean; ai_live: boolean; categories: string[]; accounts: Account[] };
type Change = { title: string; why: string; how: string; owner: string; effort: string };
type Brief = { id: number; check_id: number; url: string; mode: "live" | "template"; model: string | null; created_at: string; created_by: string | null;
  brief: { summary: string; priority_changes: Change[]; copy_suggestions: Record<string, string>; form_changes: string[];
    tracking_changes: string[]; acceptance_checks: string[]; notes: string } };

const BASE = `${API_BASE}/api/v1/landing-pages`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const SEV = { critical: "bg-danger/15 text-danger", warning: "bg-warn/15 text-warn", info: "bg-surface-2 text-muted" } as const;
const CAT: Record<string, string> = { tracking: "Tracking", intent: "Search match", cta: "Call to action", form: "Booking form", trust: "Trust",
  mobile: "Mobile", speed: "Speed", technical: "Technical" };
const COPY_LABEL: Record<string, string> = { h1: "H1", subheadline: "Sub-headline", primary_cta: "Primary CTA", secondary_cta: "Secondary CTA", trust_line: "Trust line" };
const btn = "rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2 disabled:opacity-50";
const scoreCls = (s: number) => (s >= 80 ? "text-ok" : s >= 50 ? "text-warn" : "text-danger");

function BriefView({ b }: { b: Brief }) {
  const x = b.brief;
  return (
    <div className="grid gap-3 rounded-md border border-line p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">Implementation brief</h3>
        <span className="text-xs text-muted">{b.mode === "live" ? `Claude ${b.model}` : "Template (AI off)"} · {new Date(b.created_at).toLocaleString("en-AU")}</span>
        <a href={`${BASE}/briefs/${b.id}/markdown`} className={`${btn} ml-auto`}>Download .md</a>
      </div>
      <p>{x.summary}</p>
      <ol className="grid gap-2">
        {x.priority_changes.map((c, i) => (
          <li key={i} className="rounded-md bg-surface-2 p-2">
            <div className="font-medium">{i + 1}. {c.title} <span className="text-xs font-normal text-muted">· {c.owner} · {c.effort}</span></div>
            <div className="text-xs text-muted">{c.why}</div>
            <div className="mt-1">{c.how}</div>
          </li>
        ))}
      </ol>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5 text-xs">
        {Object.entries(x.copy_suggestions).map(([k, v]) => <Fragment key={k}><dt className="text-muted">{COPY_LABEL[k] ?? k}</dt><dd>{v}</dd></Fragment>)}
      </dl>
      {([["Booking form", x.form_changes], ["Tracking", x.tracking_changes], ["How to check it's done", x.acceptance_checks]] as const).map(([t, items]) =>
        items.length > 0 && <div key={t}><div className="text-xs font-semibold uppercase text-muted">{t}</div><ul className="list-disc pl-5">{items.map((s, i) => <li key={i}>{s}</li>)}</ul></div>)}
      {x.notes && <p className="text-xs text-muted">{x.notes}</p>}
    </div>
  );
}

function PageCard({ c, aiLive, onBrief }: { c: Check; aiLive: boolean; onBrief: (msg: { ok: boolean; text: string }) => void }) {
  const [open, setOpen] = useState(false);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [busy, setBusy] = useState(false);
  const cats = [...new Set(c.findings.map((f) => f.category))];

  async function toggle() {
    setOpen((o) => !o);
    if (!brief && c.latest_brief_id) setBrief(await call<Brief>(`/briefs/${c.latest_brief_id}`).catch(() => null));
  }
  async function write() {
    setBusy(true);
    try { setBrief(await call<Brief>(`/checks/${c.id}/brief`, { method: "POST", body: JSON.stringify({ use_ai: true }) })); onBrief({ ok: true, text: "Brief ready." }); }
    catch (e) { onBrief({ ok: false, text: (e as Error).message }); }
    finally { setBusy(false); }
  }

  return (
    <li className="rounded-lg border border-line bg-surface">
      <button className="flex w-full flex-wrap items-center gap-3 p-3 text-left" onClick={toggle} aria-expanded={open}>
        <span className={`w-12 text-2xl font-semibold tabular-nums ${scoreCls(c.score)}`} aria-label={`Score ${c.score} of 100`}>{c.score}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium">{c.url}</span>
          <span className="text-xs text-muted">
            {c.ads} ad{c.ads === 1 ? "" : "s"} · ${c.cost.toFixed(2)} · {c.clicks} clicks · {c.conversions} conv. (90 days)
            {c.status_code && <> · HTTP {c.status_code}</>}{c.elapsed_ms !== null && <> · {(c.elapsed_ms / 1000).toFixed(1)}s</>}
          </span>
        </span>
        {(["critical", "warning", "info"] as const).map((s) => c.counts[s] > 0 && (
          <span key={s} className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${SEV[s]}`}>{c.counts[s]} {s}</span>
        ))}
      </button>
      {open && (
        <div className="grid gap-3 border-t border-line px-3 pb-3 pt-2 text-sm">
          {c.ad_groups.length > 0 && <p className="text-xs text-muted">Ad groups: {c.ad_groups.join(" · ")}</p>}
          {cats.map((cat) => (
            <div key={cat}>
              <div className="mb-1 text-xs font-semibold uppercase text-muted">{CAT[cat] ?? cat}</div>
              <ul className="grid gap-1.5">
                {c.findings.filter((f) => f.category === cat).map((f) => (
                  <li key={f.code + f.title} className="rounded-md bg-surface-2 p-2">
                    <div className="flex flex-wrap items-start gap-2">
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${SEV[f.severity]}`}>{f.severity}</span>
                      <span className="flex-1 font-medium">{f.title}</span>
                    </div>
                    {f.detail && <p className="mt-0.5 text-xs text-muted">{f.detail}</p>}
                    <p className="mt-1"><span className="text-xs text-muted">Fix: </span>{f.recommendation}</p>
                    {f.evidence.length > 0 && (
                      <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 text-xs">
                        {f.evidence.map(([k, v], i) => <Fragment key={i}><dt className="text-muted">{k}</dt><dd>{v}</dd></Fragment>)}
                      </dl>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {!c.findings.length && <p className="text-ok">No issues found.</p>}
          <div className="flex flex-wrap items-center gap-2">
            <button className="rounded-md bg-accent px-3 py-1 text-xs font-medium text-white disabled:opacity-50" disabled={busy} onClick={write}>
              {busy ? (aiLive ? "Claude is writing…" : "Building…") : brief ? "Rewrite brief" : "Write implementation brief"}
            </button>
            <span className="text-xs text-muted">{aiLive ? "Written by Claude from these findings." : "AI is off — a template brief is built from the findings."}</span>
          </div>
          {brief && <BriefView b={brief} />}
        </div>
      )}
    </li>
  );
}

export function LandingPagesPage() {
  const router = useRouter();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [accId, setAccId] = useState<number | null>(null);
  const [run, setRun] = useState<string>("");
  const [runs, setRuns] = useState<Run[]>([]);
  const [pages, setPages] = useState<Check[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    call<Meta>("/accounts").then((m) => { setMeta(m); if (m.accounts[0]) setAccId(m.accounts[0].id); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/landing-pages"); else setMsg({ ok: false, text: (e as Error).message }); });
  }, [router]);

  const load = useCallback(async () => {
    if (!accId) return;
    const r = await call<{ runs: Run[]; pages: Check[] }>(`/accounts/${accId}${run ? `?run=${run}` : ""}`);
    setRuns(r.runs); setPages(r.pages);
  }, [accId, run]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on selection change
    load().catch((e) => setMsg({ ok: false, text: (e as Error).message }));
  }, [load]);

  async function check() {
    setBusy(true); setMsg(null);
    try {
      const r = await call<{ run_key: string; pages: Check[] }>(`/accounts/${accId}/check`, { method: "POST" });
      setMsg({ ok: true, text: `Checked ${r.pages.length} landing page(s).` });
      if (run) setRun(""); else await load();
    } catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(false); }
  }

  const acc = meta?.accounts.find((a) => a.id === accId);
  return (
    <>
      <PageHeader title="Landing Pages" moduleId="P10">
        <div className="flex flex-wrap items-center gap-2">
          {meta && meta.accounts.length > 1 && (
            <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => { setAccId(Number(e.target.value)); setRun(""); }}>
              {meta.accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
            </select>
          )}
          {runs.length > 1 && (
            <select aria-label="Check run" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={run} onChange={(e) => setRun(e.target.value)}>
              <option value="">Latest check</option>
              {runs.slice(1).map((r) => <option key={r.run_key} value={r.run_key}>{new Date(r.checked_at).toLocaleString("en-AU")} · avg {r.avg_score}</option>)}
            </select>
          )}
          <button onClick={check} disabled={!accId || busy || !meta?.fetch_enabled} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
            {busy ? "Checking pages…" : "Check landing pages"}
          </button>
        </div>
      </PageHeader>
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      <p className="mb-4 text-sm text-muted">
        Checks every page your ads send people to ({acc?.landing_urls ?? 0} URL{acc?.landing_urls === 1 ? "" : "s"}, any of your domains) for what turns a click
        into a booking: search match, call to action, booking form, trust, mobile, speed and conversion tracking. Worst page first.
        Pages are read like a browser without JavaScript, and speed is our server&apos;s measured response time — use Google PageSpeed Insights for the full picture.
        {meta && !meta.fetch_enabled && <> Page fetching is off (flag <code>crawler.enabled</code>).</>}
      </p>
      {accId && !pages.length && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">
          No check yet. Click “Check landing pages”. {acc?.landing_urls === 0 && <>No ads with landing pages — <Link className="text-accent underline" href="/ads-accounts">sync Google Ads</Link> first.</>}
        </p>
      )}
      {pages.length > 0 && (
        <p className="mb-2 text-xs text-muted">Checked {new Date(pages[0].checked_at).toLocaleString("en-AU")}{pages[0].checked_by && <> by {pages[0].checked_by}</>}.</p>
      )}
      <ol className="grid gap-2">
        {pages.map((c) => <PageCard key={c.id} c={c} aiLive={!!meta?.ai_live} onBrief={setMsg} />)}
      </ol>
    </>
  );
}
