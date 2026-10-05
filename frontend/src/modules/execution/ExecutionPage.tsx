"use client";
// P17 — run APPROVED changes: validate with Google (changes nothing), execute (live, locked by default), roll back.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Status = { kill_switch: boolean; flag_enabled: boolean; flag_source: string; live_execution_allowed: boolean; supported_changes: string[] };
type Op = { service: string; label: string; count: number; sample: unknown[] };
type Change = { approval_id: number; title: string; change_type: string; impact: string; risk: string; decided_by: string | null;
  executable: boolean; reason: string | null; plan_hash: string | null; operations: Op[] };
type Exec = { id: number; approval_id: number; mode: string; status: string; change_type: string; error: string | null;
  resource_names: string[]; rollback_of: number | null; executed_by: string | null; created_at: string };
type Account = { id: number; customer_id: string; name: string; approved_waiting: number };

const BASE = `${API_BASE}/api/v1/execution`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const btn = "rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2 disabled:opacity-50";
const when = (s: string) => new Date(s).toLocaleString("en-AU");

function ChangeCard({ c, status, busy, onValidate, onExecute }: { c: Change; status: Status; busy: boolean;
  onValidate: () => void; onExecute: (confirm: string) => void }) {
  const [confirm, setConfirm] = useState("");
  return (
    <li className="rounded-lg border border-line bg-surface p-3 text-sm">
      <div className="flex flex-wrap items-start gap-2">
        <span className="flex-1 font-medium">{c.title}</span>
        <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] uppercase text-muted">{c.change_type}</span>
        <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] uppercase text-muted">risk {c.risk}</span>
      </div>
      {!c.executable && <p className="mt-1 text-xs text-warn">Cannot be executed here: {c.reason}</p>}
      {c.operations.map((o, i) => (
        <details key={i} className="mt-2 text-xs">
          <summary className="cursor-pointer text-muted">{o.label}</summary>
          <pre className="mt-1 max-h-48 overflow-auto rounded bg-surface-2 p-2">{JSON.stringify(o.sample, null, 1)}{o.count > o.sample.length ? `\n… +${o.count - o.sample.length} more` : ""}</pre>
        </details>
      ))}
      {c.executable && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          <button className={btn} disabled={busy} onClick={onValidate}>Validate with Google (changes nothing)</button>
          <input aria-label="Type EXECUTE" placeholder="type EXECUTE" value={confirm} onChange={(e) => setConfirm(e.target.value)}
            disabled={!status.live_execution_allowed} className="w-32 rounded-md border border-line bg-surface px-2 py-1" />
          <button className={`${btn} border-danger/40 text-danger`} disabled={busy || !status.live_execution_allowed || confirm !== "EXECUTE"}
            onClick={() => onExecute(confirm)}>Execute live</button>
          {!status.live_execution_allowed && <span className="text-muted">Live execution is locked.</span>}
        </div>
      )}
    </li>
  );
}

export function ExecutionPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accId, setAccId] = useState<number | null>(null);
  const [data, setData] = useState<{ status: Status; changes: Change[]; history: Exec[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    call<Account[]>("/accounts").then((a) => { setAccounts(a); if (a[0]) setAccId(a[0].id); })
      .catch((e) => { if ((e as { status?: number }).status === 401) router.replace("/login?next=/execution"); else setMsg({ ok: false, text: (e as Error).message }); });
  }, [router]);

  const load = useCallback(async () => {
    if (!accId) return;
    setData(await call(`/accounts/${accId}`));
  }, [accId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on account change
    load().catch((e) => setMsg({ ok: false, text: (e as Error).message }));
  }, [load]);

  async function act(path: string, ok: string, body?: object) {
    setBusy(true); setMsg(null);
    try { await call(path, { method: "POST", body: JSON.stringify(body ?? {}) }); setMsg({ ok: true, text: ok }); await load(); }
    catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(false); }
  }

  const st = data?.status;
  return (
    <>
      <PageHeader title="Google Ads Execution" moduleId="P17">
        {accounts.length > 1 && (
          <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => setAccId(Number(e.target.value))}>
            {accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
          </select>
        )}
      </PageHeader>
      {st && (
        <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${st.live_execution_allowed ? "border-danger/30 bg-danger/10 text-danger" : "border-ok/30 bg-ok/10 text-ok"}`}>
          {st.live_execution_allowed ? "LIVE execution is ON — Execute will change Google Ads."
            : `Locked: nothing here can change Google Ads (${st.kill_switch ? "kill switch is on" : "execution flag is off"}). Validate is still safe — it changes nothing.`}
        </div>
      )}
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      <p className="mb-4 text-sm text-muted">
        Only changes you already <Link href="/approvals" className="text-accent underline">approved in the Approval Center</Link> appear here.
        Supported: {st?.supported_changes.join(", ") ?? "…"}. Validate first; a live change also needs the execute permission, a typed confirmation, and
        an operator to unlock it on the server (see the manual).
      </p>
      {data && !data.changes.length && <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">No approved changes waiting.</p>}
      <ul className="mb-6 grid gap-2">
        {st && data?.changes.map((c) => (
          <ChangeCard key={c.approval_id} c={c} status={st} busy={busy}
            onValidate={() => act(`/approvals/${c.approval_id}/validate`, "Google accepted this request (nothing was changed).")}
            onExecute={(confirm) => act(`/approvals/${c.approval_id}/execute`, "Executed.", { confirm })} />
        ))}
      </ul>
      {data && data.history.length > 0 && (
        <section className="rounded-lg border border-line bg-surface p-4">
          <h2 className="mb-2 font-semibold">History</h2>
          <ul className="grid gap-1 text-xs">
            {data.history.map((h) => (
              <li key={h.id} className={h.status === "failed" ? "text-danger" : "text-muted"}>
                {when(h.created_at)} · #{h.approval_id} {h.change_type} · {h.mode} · {h.status}{h.error ? ` · ${h.error}` : ""} · {h.executed_by}
                {h.mode === "execute" && h.status === "executed" && st?.live_execution_allowed && (
                  <button className={`${btn} ml-2`} disabled={busy} onClick={() => { if (window.prompt("Type ROLLBACK to remove what this created") === "ROLLBACK") void act(`/executions/${h.id}/rollback`, "Rolled back.", { confirm: "ROLLBACK" }); }}>Roll back</button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
