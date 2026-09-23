"use client";
// P01 — Settings (read-only). Shows environment health and feature flags from P00.
// Editing flags needs P02 auth + P22 audit; users/roles move here from P02.
import { PageHeader } from "@/shell";
import { useFoundation, type Flag, type Health } from "@/shell/api";

export default function SettingsPage() {
  const health = useFoundation<Health>("health");
  const flags = useFoundation<Flag[]>("flags");

  return (
    <>
      <PageHeader title="Settings" moduleId="P01" />

      <section className="rounded-lg border border-line bg-surface p-4">
        <h2 className="mb-2 font-semibold">Environment</h2>
        {health.error ? (
          <p className="text-sm text-danger">Backend unreachable: {health.error}</p>
        ) : (
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
            <dt className="text-muted">Environment</dt><dd>{health.data?.env ?? "…"}</dd>
            <dt className="text-muted">Database</dt><dd>{health.data ? (health.data.database ? "connected" : "error") : "…"}</dd>
            <dt className="text-muted">Execution kill switch</dt>
            <dd>{health.data ? (health.data.execution_kill_switch ? "ON — live Google Ads changes are blocked" : "OFF") : "…"}</dd>
          </dl>
        )}
      </section>

      <section className="mt-4 rounded-lg border border-line bg-surface p-4">
        <h2 className="mb-2 font-semibold">Feature flags</h2>
        <p className="mb-3 text-xs text-muted">Read-only. All flags default off.</p>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted">
              <tr><th className="py-1 pr-4 font-medium">Flag</th><th className="pr-4 font-medium">Module</th><th className="pr-4 font-medium">State</th><th className="font-medium">Why</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {(flags.data ?? []).map((f) => (
                <tr key={f.key}>
                  <td className="py-1.5 pr-4 font-mono text-xs">{f.key}</td>
                  <td className="pr-4">{f.module_id}</td>
                  <td className={`pr-4 ${f.enabled ? "text-ok" : "text-muted"}`}>{f.enabled ? "on" : "off"}</td>
                  <td className="text-muted">{f.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {flags.error && <p className="text-sm text-danger">Could not load flags: {flags.error}</p>}
        </div>
      </section>
    </>
  );
}
