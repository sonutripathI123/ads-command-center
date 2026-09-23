"use client";
// P01 — Overview. Shows scope + build progress only; business KPIs arrive with P05/P13/P19.
import Link from "next/link";
import { PageHeader, SCOPE_ALL, useModuleStatus, useScope } from "@/shell";

const SETUP = [
  { step: "Add websites", moduleId: "P03", href: "/websites" },
  { step: "Connect Google Ads", moduleId: "P04", href: "/ads-accounts" },
  { step: "Connect GA4 / bookings", moduleId: "P06", href: "/conversions" },
  { step: "Import Ads history", moduleId: "P05", href: "/campaigns" },
  { step: "Run first audit", moduleId: "P07", href: "/recommendations" },
];

export default function OverviewPage() {
  const { websites, adsAccounts, websiteId } = useScope();
  const { modules, loading } = useModuleStatus();
  const done = (modules ?? []).filter((m) => m.status === "approved_frozen").length;
  const inReview = (modules ?? []).filter((m) => m.status === "review").length;
  const statusOf = (id: string) => modules?.find((m) => m.id === id)?.status ?? "planned";

  return (
    <>
      <PageHeader title="Overview" moduleId="P01" />

      <div className="grid gap-3 sm:grid-cols-3">
        <Tile label="Websites in scope" value={websiteId === SCOPE_ALL ? String(websites.length) : "1"} note="demo list" />
        <Tile label="Ads accounts" value={String(adsAccounts.length)} note="demo list" />
        <Tile
          label="Modules approved"
          value={loading ? "…" : modules ? `${done} / ${modules.length}` : "—"}
          note={modules ? `${inReview} in review` : "backend offline"}
        />
      </div>

      <section className="mt-6 rounded-lg border border-line bg-surface p-4">
        <h2 className="mb-3 font-semibold">Getting started</h2>
        <ol className="flex flex-col divide-y divide-line">
          {SETUP.map((s, i) => (
            <li key={s.step} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span>
                <span className="mr-2 text-muted">{i + 1}.</span>
                <Link href={s.href} className="hover:underline">{s.step}</Link>
              </span>
              <span className="text-xs text-muted">{s.moduleId} · {statusOf(s.moduleId)}</span>
            </li>
          ))}
        </ol>
      </section>

      <p className="mt-4 text-xs text-muted">
        Spend, conversions, bookings and revenue appear here once P05 (Ads sync) and P13 (Booking funnel) are live.
      </p>
    </>
  );
}

function Tile({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-1 text-3xl font-semibold tabular-nums">{value}</div>
      <div className="mt-1 text-xs text-muted">{note}</div>
    </div>
  );
}
