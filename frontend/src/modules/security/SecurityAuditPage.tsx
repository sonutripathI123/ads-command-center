"use client";
// P22 — audit log: read-only, admin-only trail of security-sensitive actions with before/after values.
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Row = { id: number; at: string; module_id: string; action: string; actor: string | null; actor_role: string | null;
  entity_type: string | null; entity_id: string | null; before: unknown; after: unknown; note: string | null;
  request_id: string | null; ip: string | null };
type ListResp = { rows: Row[]; total: number; limit: number; offset: number };
type Facets = { modules: string[]; actions: string[] };

const BASE = `${API_BASE}/api/v1/security`;
async function call<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { credentials: "include" });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const input = "rounded-md border border-line bg-surface px-2 py-1 text-sm";
const PAGE_SIZE = 25;
const when = (s: string) => new Date(s).toLocaleString("en-AU");

function Diff({ before, after }: { before: unknown; after: unknown }) {
  const b = JSON.stringify(before);
  const a = JSON.stringify(after);
  if (b === "null" && a === "null") return null;
  return (
    <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
      {b !== "null" && <><dt className="text-muted">Before</dt><dd className="truncate font-mono">{b}</dd></>}
      {a !== "null" && <><dt className="text-muted">After</dt><dd className="truncate font-mono">{a}</dd></>}
    </dl>
  );
}

export function SecurityAuditPage() {
  const router = useRouter();
  const [facets, setFacets] = useState<Facets | null>(null);
  const [f, setF] = useState({ module_id: "", actor: "", action: "", entity_type: "", entity_id: "" });
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<ListResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    call<Facets>("/audit-logs/facets").catch((e) => {
      if ((e as { status?: number }).status === 401) router.replace("/login?next=/audit-log");
      else if ((e as { status?: number }).status !== 403) setErr((e as Error).message);
    }).then((v) => v && setFacets(v));
  }, [router]);

  const load = useCallback(async () => {
    const q = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
    for (const [k, v] of Object.entries(f)) if (v) q.set(k, v);
    try {
      setData(await call<ListResp>(`/audit-logs?${q}`));
      setErr(null);
    } catch (e) {
      if ((e as { status?: number }).status === 403) setErr("forbidden");
      else setErr((e as Error).message);
    }
  }, [f, offset]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on filter/page change
    load();
  }, [load]);

  function setFilter(k: keyof typeof f, v: string) {
    setF((x) => ({ ...x, [k]: v }));
    setOffset(0);
  }

  if (err === "forbidden") {
    return (
      <>
        <PageHeader title="Audit Log" moduleId="P22" />
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">
          Admin permission required to view the audit log.
        </p>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Audit Log" moduleId="P22" />
      {err && <div role="status" className="mb-4 rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{err}</div>}
      <p className="mb-4 text-sm text-muted">
        Every approval decision and ad draft review, with who did it and the before/after values. Append-only — nothing here can be edited or deleted.
      </p>
      <div className="mb-3 flex flex-wrap items-end gap-2 text-sm">
        <label className="text-xs text-muted">Module<br />
          <select className={input} value={f.module_id} onChange={(e) => setFilter("module_id", e.target.value)}>
            <option value="">All</option>
            {(facets?.modules ?? []).map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>
        <label className="text-xs text-muted">Action<br />
          <select className={input} value={f.action} onChange={(e) => setFilter("action", e.target.value)}>
            <option value="">All</option>
            {(facets?.actions ?? []).map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </label>
        <label className="text-xs text-muted">Actor<br />
          <input className={input} placeholder="email" value={f.actor} onChange={(e) => setFilter("actor", e.target.value)} />
        </label>
        <label className="text-xs text-muted">Entity type<br />
          <input className={input} placeholder="approval, ad_draft…" value={f.entity_type} onChange={(e) => setFilter("entity_type", e.target.value)} />
        </label>
        <label className="text-xs text-muted">Entity id<br />
          <input className={input} value={f.entity_id} onChange={(e) => setFilter("entity_id", e.target.value)} />
        </label>
      </div>
      {data && !data.rows.length && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">No matching entries.</p>
      )}
      {data && data.rows.length > 0 && (
        <>
          <ol className="grid gap-2">
            {data.rows.map((r) => (
              <li key={r.id} className="rounded-lg border border-line bg-surface p-3 text-sm">
                <div className="flex flex-wrap items-start gap-2">
                  <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-muted">{r.module_id}</span>
                  <span className="flex-1 font-medium">{r.action}</span>
                  <span className="text-xs text-muted">{when(r.at)}</span>
                </div>
                <p className="mt-1 text-xs text-muted">
                  {r.actor ?? "system"}{r.actor_role && <> ({r.actor_role})</>}
                  {r.entity_type && <> · {r.entity_type} #{r.entity_id}</>}
                </p>
                <Diff before={r.before} after={r.after} />
                {r.note && <p className="mt-1 text-xs text-muted">Note: {r.note}</p>}
              </li>
            ))}
          </ol>
          <div className="mt-3 flex items-center justify-between text-xs text-muted">
            <span>{offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of {data.total}</span>
            <div className="flex gap-2">
              <button className="rounded-md border border-line px-2.5 py-1 hover:bg-surface-2 disabled:opacity-50"
                disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</button>
              <button className="rounded-md border border-line px-2.5 py-1 hover:bg-surface-2 disabled:opacity-50"
                disabled={offset + PAGE_SIZE >= data.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
