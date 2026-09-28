"use client";
// P01 — global status: backend health + kill switch. Real alerts arrive from P18 later.
import type { Health } from "./api";

type Tone = "ok" | "warn" | "danger" | "info";
const toneCls: Record<Tone, string> = {
  ok: "border-ok/30 bg-ok/10 text-ok",
  warn: "border-warn/30 bg-warn/10 text-warn",
  danger: "border-danger/30 bg-danger/10 text-danger",
  info: "border-line bg-surface-2 text-muted",
};

function Pill({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${toneCls[tone]}`}>{children}</span>;
}

export function StatusPills({ health, error, loading }: { health: Health | null; error: string | null; loading: boolean }) {
  if (loading) return <Pill tone="info">Checking backend…</Pill>;
  if (error || !health) return <Pill tone="danger">Backend offline</Pill>;
  return (
    <>
      <Pill tone={health.status === "ok" ? "ok" : "warn"}>API {health.status}</Pill>
      <Pill tone={health.execution_kill_switch ? "ok" : "danger"}>
        {health.execution_kill_switch ? "Live execution locked" : "Kill switch OFF"}
      </Pill>
    </>
  );
}

export function AlertStrip({ error }: { error: string | null }) {
  return (
    <div className="flex flex-col gap-1 px-4 pt-3 sm:px-6" role="status">
      {error && (
        <div className={`rounded-md border px-3 py-2 text-sm ${toneCls.danger}`}>
          Can’t reach the backend ({error}). Start it with <code>uvicorn app.main:app</code> in <code>backend/</code>.
        </div>
      )}
    </div>
  );
}
