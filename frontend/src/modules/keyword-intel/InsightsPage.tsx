"use client";
// P08 — keyword insights: wasters, winners, low Quality Score, duplicates, idle, new keyword ideas.
import { useEffect, useState } from "react";
import { AdsDataFrame, money, num, title, type FrameCtx } from "@/modules/ads-sync";
import { kwApi, type InsightRow, type Insights } from "./api";

const SECTIONS: { key: keyof Omit<Insights, "enabled_campaigns">; label: string; help: string }[] = [
  { key: "wasters", label: "Keywords spending without conversions", help: "Consider pausing, lowering bids, or tightening match type." },
  { key: "winners", label: "Keywords that convert", help: "Cheapest cost per conversion first — protect their budget." },
  { key: "expansion_candidates", label: "New keyword ideas", help: "Searches that converted but aren't keywords yet." },
  { key: "low_quality_score", label: "Low Quality Score (≤ 4)", help: "Improve ad relevance and landing page to lower CPC." },
  { key: "duplicates", label: "Duplicate keywords (same campaign)", help: "Same keyword in several ad groups competes with itself." },
  { key: "idle", label: "Enabled keywords with no impressions", help: "Only counts campaigns that are running." },
];
const SHOW = 25;

export function InsightsPage() {
  return <AdsDataFrame title="Keyword insights" moduleId="P08">{(ctx) => <Body {...ctx} />}</AdsDataFrame>;
}

function label(r: InsightRow) {
  return String(r.text ?? r.search_term ?? "");
}

function Body({ accountId, days, currency, refreshKey }: FrameCtx) {
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let live = true;
    kwApi.insights(accountId, days).then((d) => live && setData(d)).catch((e: Error) => live && setError(e.message));
    return () => { live = false; };
  }, [accountId, days, refreshKey]);

  if (error) return <p className="text-sm text-danger">{error}</p>;
  if (!data) return <p className="text-sm text-muted">Loading…</p>;
  return (
    <>
      {data.enabled_campaigns === 0 && (
        <div className="mb-4 rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn" role="status">
          ⚠ No campaign is currently enabled, so “idle” and “duplicate” checks are empty.
        </div>
      )}
      <div className="grid gap-4">
        {SECTIONS.map((s) => {
          const rows = data[s.key];
          const shown = expanded[s.key] ? rows : rows.slice(0, SHOW);
          return (
            <section key={s.key} className="rounded-lg border border-line bg-surface p-4">
              <h2 className="font-semibold">{s.label} <span className="text-sm font-normal text-muted">({rows.length})</span></h2>
              <p className="mb-2 text-xs text-muted">{s.help}</p>
              {!rows.length ? <p className="text-sm text-muted">None 🎉</p> : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs text-muted">
                      <tr><th className="py-1 pr-4 font-medium">{s.key === "expansion_candidates" ? "Search term" : "Keyword"}</th>
                        <th className="pr-4 font-medium">Match</th><th className="pr-4 font-medium">Ad group</th><th className="pr-4 font-medium">Why</th>
                        <th className="pr-4 text-right font-medium">Cost</th><th className="pr-4 text-right font-medium">Clicks</th>
                        <th className="pr-4 text-right font-medium">Conv.</th><th className="text-right font-medium">Cost / conv.</th></tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {shown.map((r, i) => (
                        <tr key={`${label(r)}-${String(r.key ?? i)}`}>
                          <td className="py-1.5 pr-4 font-medium">{label(r)}</td>
                          <td className="pr-4 text-xs">{title((r.match_type ?? r.matched_match_type) as string | null)}</td>
                          <td className="pr-4 text-xs text-muted">{String(r.ad_group_name ?? "")}</td>
                          <td className="pr-4 text-xs">{r.reason}</td>
                          <td className="pr-4 text-right tabular-nums">{money(r.cost, currency)}</td>
                          <td className="pr-4 text-right tabular-nums">{num(r.clicks)}</td>
                          <td className="pr-4 text-right tabular-nums">{num(r.conversions, 1)}</td>
                          <td className="text-right tabular-nums">{money(r.cost_per_conversion as number | null, currency)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {rows.length > SHOW && (
                    <button className="mt-2 text-sm text-accent" onClick={() => setExpanded({ ...expanded, [s.key]: !expanded[s.key] })}>
                      {expanded[s.key] ? "Show less" : `Show all ${rows.length}`}
                    </button>
                  )}
                </div>
              )}
            </section>
          );
        })}
      </div>
    </>
  );
}
