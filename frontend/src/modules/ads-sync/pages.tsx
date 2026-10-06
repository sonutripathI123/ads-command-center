"use client";
// P05 — data pages. Each renders inside AdsDataFrame (account, range, sync).
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AdsDataFrame, type FrameCtx } from "./AdsDataFrame";
import { syncApi, type AdGroupRow, type CampaignRow, type KeywordRow, type Metrics, type SearchTermRow, type Summary } from "./api";
import { DataTable, type Column } from "./DataTable";
import { money, num, pct, title } from "./format";
import { SpendChart } from "./SpendChart";

const card = "rounded-lg border border-line bg-surface p-4";

function useData<T>(fetcher: () => Promise<T>, deps: unknown[]): { data: T | null; error: string | null } {
  const [state, setState] = useState<{ data: T | null; error: string | null }>({ data: null, error: null });
  useEffect(() => {
    let live = true;
    fetcher().then((data) => live && setState({ data, error: null }))
      .catch((e: Error) => live && setState({ data: null, error: e.message }));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

function metricColumns<T extends Metrics>(currency: string): Column<T>[] {
  return [
    { key: "cost", label: "Cost", numeric: true, value: (r) => r.cost, render: (r) => money(r.cost, currency) },
    { key: "clicks", label: "Clicks", numeric: true, value: (r) => r.clicks, render: (r) => num(r.clicks) },
    { key: "impressions", label: "Impr.", numeric: true, value: (r) => r.impressions, render: (r) => num(r.impressions) },
    { key: "ctr", label: "CTR", numeric: true, value: (r) => r.ctr, render: (r) => pct(r.ctr) },
    { key: "avg_cpc", label: "Avg CPC", numeric: true, value: (r) => r.avg_cpc, render: (r) => money(r.avg_cpc, currency) },
    { key: "conversions", label: "Conv.", numeric: true, value: (r) => r.conversions, render: (r) => num(r.conversions, 1) },
    { key: "cost_per_conversion", label: "Cost / conv.", numeric: true, value: (r) => r.cost_per_conversion, render: (r) => money(r.cost_per_conversion, currency) },
  ];
}

const STATUS_LABEL: Record<string, string> = { CAMPAIGN_PAUSED: "Campaign paused", CAMPAIGN_REMOVED: "Campaign removed", REMOVED: "Removed" };
const Status = ({ s }: { s: string | null }) => (
  <span className={`text-xs ${s === "ENABLED" ? "text-ok" : "text-muted"}`}>{s === "ENABLED" ? "● " : "○ "}{(s && STATUS_LABEL[s]) || title(s)}</span>
);

function ShowRemoved({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-1.5 text-xs text-muted">
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)} /> Show removed
    </label>
  );
}

function Loading({ error }: { error: string | null }) {
  return error ? <p className="text-sm text-danger">{error}</p> : <p className="text-sm text-muted">Loading…</p>;
}

// ---- Campaigns --------------------------------------------------------------------

export function CampaignsPage() {
  return <AdsDataFrame title="Campaigns">{(ctx) => <CampaignsBody {...ctx} />}</AdsDataFrame>;
}

function CampaignsBody({ accountId, days, currency, refreshKey }: FrameCtx) {
  const [showRemoved, setShowRemoved] = useState(false);
  const summary = useData<Summary>(() => syncApi.summary(accountId, days), [accountId, days, refreshKey]);
  const rows = useData<CampaignRow[]>(() => syncApi.campaigns(accountId, days, showRemoved), [accountId, days, showRemoved, refreshKey]);
  const cols = useMemo<Column<CampaignRow>[]>(() => [
    { key: "name", label: "Campaign", value: (r) => r.name, render: (r) => <span className="font-medium">{r.name}</span> },
    { key: "status", label: "Status", value: (r) => r.status, render: (r) => <Status s={r.status} /> },
    { key: "channel_type", label: "Type", value: (r) => r.channel_type, render: (r) => title(r.channel_type) },
    { key: "budget", label: "Budget/day", numeric: true, value: (r) => r.budget, render: (r) => money(r.budget, currency) },
    ...metricColumns<CampaignRow>(currency),
  ], [currency]);
  const t = summary.data?.totals;
  const allPaused = rows.data && rows.data.length > 0 && rows.data.every((r) => r.status !== "ENABLED");

  return (
    <>
      {allPaused && (
        <div className="mb-4 rounded-md border border-warn/30 bg-warn/10 px-3 py-2 text-sm text-warn" role="status">
          ⚠ All campaigns in this account are paused — no ads are running right now.
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Tile label="Spend" value={t ? money(t.cost, currency) : "…"} />
        <Tile label="Clicks" value={t ? num(t.clicks) : "…"} note={t ? `CTR ${pct(t.ctr)}` : undefined} />
        <Tile label="Avg CPC" value={t ? money(t.avg_cpc, currency) : "…"} />
        <Tile label="Conversions" value={t ? num(t.conversions, 1) : "…"} note={t ? `Conv. rate ${pct(t.conv_rate)}` : undefined} />
        <Tile label="Cost / conversion" value={t ? money(t.cost_per_conversion, currency) : "…"} />
      </div>
      <section className={`${card} mt-4`}>
        {summary.data ? <SpendChart daily={summary.data.daily} currency={currency} /> : <Loading error={summary.error} />}
      </section>
      <section className={`${card} mt-4`}>
        <div className="mb-2 flex items-center gap-3"><h2 className="font-semibold">Campaigns · last {days} days</h2><span className="ml-auto"><ShowRemoved value={showRemoved} onChange={setShowRemoved} /></span></div>
        {rows.data ? <DataTable rows={rows.data} columns={cols} rowKey={(r) => r.google_id} initialSort="cost" /> : <Loading error={rows.error} />}
      </section>
      <p className="mt-3 text-xs text-muted">Conversions are as counted by Google Ads (not confirmed bookings — those arrive with P06/P13).</p>
    </>
  );
}

function Tile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className={card}>
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {note && <div className="mt-1 text-xs text-muted">{note}</div>}
    </div>
  );
}

// ---- Campaign filter (shared) ---------------------------------------------------------

function CampaignFilter({ accountId, days, value, onChange }: { accountId: number; days: number; value: string; onChange: (v: string) => void }) {
  const camps = useData<CampaignRow[]>(() => syncApi.campaigns(accountId, days), [accountId, days]);
  return (
    <select className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={value} onChange={(e) => onChange(e.target.value)}
      aria-label="Filter by campaign">
      <option value="">All campaigns</option>
      {camps.data?.map((c) => <option key={c.google_id} value={c.google_id}>{c.name}</option>)}
    </select>
  );
}

// ---- Ad groups ------------------------------------------------------------------------

export function AdGroupsPage() {
  return <AdsDataFrame title="Ad Groups">{(ctx) => <AdGroupsBody {...ctx} />}</AdsDataFrame>;
}

function AdGroupsBody({ accountId, days, currency, refreshKey }: FrameCtx) {
  const [campaign, setCampaign] = useState("");
  const [showRemoved, setShowRemoved] = useState(false);
  const rows = useData<AdGroupRow[]>(() => syncApi.adGroups(accountId, days, campaign || undefined, showRemoved), [accountId, days, campaign, showRemoved, refreshKey]);
  const cols = useMemo<Column<AdGroupRow>[]>(() => [
    { key: "name", label: "Ad group", value: (r) => r.name, render: (r) => <span className="font-medium">{r.name}</span> },
    { key: "campaign_name", label: "Campaign", value: (r) => r.campaign_name, render: (r) => r.campaign_name || <span className="text-muted">(removed campaign)</span> },
    { key: "status", label: "Status", value: (r) => r.effective_status, render: (r) => <Status s={r.effective_status} /> },
    ...metricColumns<AdGroupRow>(currency),
  ], [currency]);
  return (
    <section className={card}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="font-semibold">Ad groups · last {days} days</h2>
        <span className="ml-auto flex items-center gap-3"><ShowRemoved value={showRemoved} onChange={setShowRemoved} />
          <CampaignFilter accountId={accountId} days={days} value={campaign} onChange={setCampaign} /></span>
      </div>
      {rows.data ? <DataTable rows={rows.data} columns={cols} rowKey={(r) => r.google_id} initialSort="cost" /> : <Loading error={rows.error} />}
    </section>
  );
}

// ---- Keywords -------------------------------------------------------------------------

export function KeywordsPage() {
  return <AdsDataFrame title="Keywords">{(ctx) => <KeywordsBody {...ctx} />}</AdsDataFrame>;
}

function KeywordsBody({ accountId, days, currency, refreshKey }: FrameCtx) {
  const [campaign, setCampaign] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);
  const rows = useData<KeywordRow[]>(() => syncApi.keywords(accountId, days, campaign || undefined), [accountId, days, campaign, refreshKey]);
  const shown = useMemo(() => (rows.data ?? []).filter((r) => !activeOnly || r.impressions > 0), [rows.data, activeOnly]);
  const cols = useMemo<Column<KeywordRow>[]>(() => [
    { key: "text", label: "Keyword", value: (r) => r.text, render: (r) => <span className="font-medium">{r.text}</span> },
    { key: "match_type", label: "Match", value: (r) => r.match_type, render: (r) => title(r.match_type) },
    { key: "quality_score", label: "QS", numeric: true, value: (r) => r.quality_score, render: (r) => r.quality_score ?? "—" },
    { key: "ad_group_name", label: "Ad group", value: (r) => r.ad_group_name },
    { key: "status", label: "Status", value: (r) => r.status, render: (r) => <Status s={r.status} /> },
    ...metricColumns<KeywordRow>(currency),
  ], [currency]);
  return (
    <section className={card}>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h2 className="font-semibold">Keywords · last {days} days</h2>
        <Link href="/keywords/insights" className="rounded-md bg-accent-soft px-2.5 py-1 text-sm font-medium text-accent">Keyword insights →</Link>
        <label className="ml-auto flex items-center gap-1.5 text-sm">
          <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} /> Only with impressions
        </label>
        <CampaignFilter accountId={accountId} days={days} value={campaign} onChange={setCampaign} />
      </div>
      {rows.data ? <DataTable rows={shown} columns={cols} rowKey={(r) => r.key} initialSort="cost" /> : <Loading error={rows.error} />}
    </section>
  );
}

// ---- Search terms ---------------------------------------------------------------------

export function SearchTermsPage() {
  return <AdsDataFrame title="Search Terms">{(ctx) => <SearchTermsBody {...ctx} />}</AdsDataFrame>;
}

function SearchTermsBody({ accountId, days, currency, refreshKey }: FrameCtx) {
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const rows = useData<SearchTermRow[]>(() => syncApi.searchTerms(accountId, days, query || undefined), [accountId, days, query, refreshKey]);
  const wasted = useMemo(() => (rows.data ?? []).filter((r) => r.conversions === 0).reduce((s, r) => s + r.cost, 0), [rows.data]);
  const cols = useMemo<Column<SearchTermRow>[]>(() => [
    { key: "search_term", label: "Search term", value: (r) => r.search_term, render: (r) => <span className="font-medium">{r.search_term}</span> },
    { key: "matched_keyword", label: "Matched keyword", value: (r) => r.matched_keyword,
      render: (r) => <span className="text-muted">{r.matched_keyword ?? "—"} {r.matched_match_type ? `(${title(r.matched_match_type)})` : ""}</span> },
    { key: "campaign_name", label: "Campaign", value: (r) => r.campaign_name },
    { key: "status", label: "Added?", value: (r) => r.status, render: (r) => title(r.status === "NONE" ? "—" : r.status) },
    ...metricColumns<SearchTermRow>(currency),
  ], [currency]);
  return (
    <section className={card}>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h2 className="font-semibold">Search terms · last {days} days</h2>
        <Link href="/search-terms/negatives" className="rounded-md bg-accent-soft px-2.5 py-1 text-sm font-medium text-accent">Negative keyword suggestions →</Link>
        <form className="ml-auto flex gap-2" onSubmit={(e) => { e.preventDefault(); setQuery(q.trim()); }}>
          <input className="rounded-md border border-line bg-surface px-2 py-1 text-sm" placeholder="Filter, e.g. cheap" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="rounded-md border border-line px-2.5 py-1 text-sm">Filter</button>
        </form>
      </div>
      {rows.data && (
        <p className="mb-3 text-sm text-muted">
          Spend on search terms with <b>0 conversions</b>: <span className="font-medium text-fg">{money(wasted, currency)}</span>
          {" "}— review the <Link className="text-accent underline" href="/search-terms/negatives">negative keyword suggestions</Link>.
        </p>
      )}
      {rows.data ? <DataTable rows={rows.data} columns={cols} rowKey={(r) => r.key} initialSort="cost" /> : <Loading error={rows.error} />}
    </section>
  );
}
