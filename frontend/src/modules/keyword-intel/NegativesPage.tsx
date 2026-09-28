"use client";
// P08 — negative keyword review: run analysis, filter by status/confidence, accept/reject, export.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AdsDataFrame, money, num, type FrameCtx } from "@/modules/ads-sync";
import { asGoogleAds, kwApi, type AnalyzeResult, type Negative } from "./api";

const STATUSES = [
  { key: "proposed", label: "To review" }, { key: "accepted", label: "Accepted" },
  { key: "rejected", label: "Rejected" }, { key: "stale", label: "No longer seen" },
] as const;
const CONFIDENCE = [
  { v: 0, label: "All" }, { v: 0.5, label: "≥ 50%" }, { v: 0.8, label: "≥ 80%" }, { v: 0.9, label: "≥ 90%" },
];
const INTENT_LABEL: Record<string, string> = {
  service_location: "Service + area", service: "Service only", location_only: "Area only", excluded: "Excluded words",
  wrong_location: "Wrong location", competitor: "Competitor", brand: "Your brand", unclassified: "Unrecognised",
};

export function NegativesPage() {
  return (
    <AdsDataFrame title="Negative keyword suggestions" moduleId="P08">
      {(ctx) => <Body {...ctx} />}
    </AdsDataFrame>
  );
}

function Confidence({ v }: { v: number }) {
  const tone = v >= 0.8 ? "text-ok border-ok/30 bg-ok/10" : v >= 0.5 ? "text-warn border-warn/30 bg-warn/10" : "text-muted border-line";
  return <span className={`rounded-full border px-2 py-0.5 text-xs tabular-nums ${tone}`}>{Math.round(v * 100)}%</span>;
}

function Body({ accountId, days, currency, refreshKey }: FrameCtx) {
  const [status, setStatus] = useState<string>("proposed");
  const [minConf, setMinConf] = useState(0);
  const [rows, setRows] = useState<Negative[] | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [run, setRun] = useState<AnalyzeResult | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [open, setOpen] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setRows(await kwApi.negatives(accountId, status, minConf));
      setSelected(new Set());
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  }, [accountId, status, minConf]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on filter change
    load();
  }, [load, refreshKey]);

  async function analyze() {
    setBusy("analyze");
    setMsg(null);
    try {
      setRun(await kwApi.analyze(accountId, days));
      await load();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(null);
    }
  }

  async function review(to: "accepted" | "rejected" | "proposed") {
    if (!selected.size) return;
    setBusy(to);
    try {
      const r = await kwApi.review(accountId, [...selected], to);
      setMsg({ ok: true, text: `${r.updated} suggestion(s) marked ${to}.` });
      await load();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(null);
    }
  }

  async function copy() {
    try {
      const text = await kwApi.exportText(accountId);
      await navigator.clipboard.writeText(text);
      setMsg({ ok: true, text: `Copied ${text.trim().split("\n").filter(Boolean).length} accepted negative(s). Paste them in Google Ads → Keywords → Negative keywords.` });
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  }

  const all = rows ?? [];
  const allChecked = all.length > 0 && all.every((r) => selected.has(r.id));
  const toggle = (id: number) => setSelected((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const btn = "rounded-md border border-line px-2.5 py-1 text-sm hover:bg-surface-2 disabled:opacity-50";

  return (
    <>
      <section className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-line bg-surface p-4">
        <div className="text-sm">
          <div className="font-semibold">Analyse the last {days} days of search terms</div>
          <div className="text-muted">Uses your <Link className="text-accent underline" href="/business-rules">Business Rules</Link>. Nothing is changed in Google Ads.</div>
        </div>
        <button onClick={analyze} disabled={!!busy} className="ml-auto rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
          {busy === "analyze" ? "Analysing…" : "Run analysis"}
        </button>
        {run && (
          <div className="w-full border-t border-line pt-3 text-sm">
            <p>
              {num(run.search_terms)} search terms · <b>{run.negative_candidates}</b> negative suggestions ·
              high-confidence wasted spend <b>{money(run.high_confidence_waste, currency)}</b> · {run.expansion_candidates} new keyword ideas
              (<Link className="text-accent underline" href="/keywords/insights">see insights</Link>)
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {Object.entries(run.intents).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                <span key={k} className="rounded-full border border-line px-2 py-0.5 text-xs text-muted">{INTENT_LABEL[k] ?? k}: <b className="text-fg">{v}</b></span>
              ))}
            </div>
          </div>
        )}
      </section>

      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}

      <section className="rounded-lg border border-line bg-surface p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div role="tablist" className="flex overflow-hidden rounded-md border border-line">
            {STATUSES.map((s) => (
              <button key={s.key} role="tab" aria-selected={status === s.key} onClick={() => setStatus(s.key)}
                className={`px-2.5 py-1 text-sm ${status === s.key ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"}`}>{s.label}</button>
            ))}
          </div>
          <label className="flex items-center gap-1.5 text-sm">Confidence
            <select className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={minConf} onChange={(e) => setMinConf(Number(e.target.value))}>
              {CONFIDENCE.map((c) => <option key={c.v} value={c.v}>{c.label}</option>)}
            </select>
          </label>
          <span className="ml-auto flex flex-wrap gap-2">
            {status !== "accepted" && <button className={btn} disabled={!selected.size || !!busy} onClick={() => review("accepted")}>Accept ({selected.size})</button>}
            {status !== "rejected" && <button className={btn} disabled={!selected.size || !!busy} onClick={() => review("rejected")}>Reject</button>}
            {status !== "proposed" && <button className={btn} disabled={!selected.size || !!busy} onClick={() => review("proposed")}>Back to review</button>}
            {status === "accepted" && <>
              <button className={btn} onClick={copy} disabled={!all.length}>Copy for Google Ads</button>
              <a className={btn} href={kwApi.csvUrl(accountId)}>Download CSV</a>
            </>}
          </span>
        </div>

        {!rows ? <p className="text-sm text-muted">Loading…</p> : !all.length ? (
          <p className="py-6 text-center text-sm text-muted">
            {status === "proposed" ? "Nothing to review. Click “Run analysis” to find wasted search terms." : "Nothing here."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-muted">
                <tr>
                  <th className="w-8 py-1.5"><input type="checkbox" aria-label="Select all" checked={allChecked}
                    onChange={() => setSelected(allChecked ? new Set() : new Set(all.map((r) => r.id)))} /></th>
                  <th className="pr-4 font-medium">Negative keyword</th><th className="pr-4 font-medium">Where</th>
                  <th className="pr-4 font-medium">Why</th><th className="pr-4 text-right font-medium">Wasted</th>
                  <th className="pr-4 text-right font-medium">Clicks</th><th className="pr-4 text-right font-medium">Conv.</th>
                  <th className="pr-4 text-right font-medium">Searches</th><th className="font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {all.map((r) => (
                  <tr key={r.id} className="align-top hover:bg-surface-2">
                    <td className="py-2"><input type="checkbox" aria-label={`Select ${r.text}`} checked={selected.has(r.id)} onChange={() => toggle(r.id)} /></td>
                    <td className="py-2 pr-4 font-mono text-xs">{asGoogleAds(r)}<div className="font-sans text-xs text-muted">{r.match_type === "PHRASE" ? "Phrase" : "Exact"}</div></td>
                    <td className="py-2 pr-4 text-xs">{r.level === "account" ? "All campaigns" : r.campaign_name ?? r.campaign_google_id}</td>
                    <td className="max-w-md py-2 pr-4 text-xs">
                      {r.reason}
                      <button className="ml-1 text-accent" onClick={() => setOpen(open === r.id ? null : r.id)}>{open === r.id ? "hide" : "examples"}</button>
                      {open === r.id && <ul className="mt-1 list-disc pl-4 text-muted">{r.examples.map((x) => <li key={x}>{x}</li>)}</ul>}
                    </td>
                    <td className="py-2 pr-4 text-right tabular-nums">{money(r.cost, currency)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{num(r.clicks)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{num(r.conversions, 1)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{r.term_count}</td>
                    <td className="py-2"><Confidence v={r.confidence} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-xs text-muted">
              {all.length} suggestions · total wasted {money(all.reduce((s, r) => s + r.cost, 0), currency)}.
              Accepted negatives are <b>not</b> sent to Google Ads automatically — copy/paste them yourself (automatic push comes with P16/P17 approvals).
            </p>
          </div>
        )}
      </section>
    </>
  );
}
