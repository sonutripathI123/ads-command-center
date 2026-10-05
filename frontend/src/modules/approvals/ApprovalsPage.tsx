"use client";
// P16 — Approval Center: every proposed Google Ads change, with before/after, evidence and a recorded decision.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Json = string | number | boolean | null | Json[] | { [k: string]: Json };
type Approval = {
  id: number; source_module: string; change_type: string; impact: "standard" | "high"; risk: string; title: string;
  before: Record<string, Json>; after: Record<string, Json>; evidence: [string, string][]; status: string;
  requested_by: string | null; decided_by: string | null; decided_at: string | null; decision_note: string | null;
  executed_at: string | null; execution_result: string | null; created_at: string; confirm_required: string | null;
  history?: { event: string; by: string | null; note: string | null; at: string }[];
};
type Account = { id: number; customer_id: string; name: string; counts: Record<string, number> };

const BASE = `${API_BASE}/api/v1/approvals`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const TABS = [["pending", "Pending"], ["approved", "Approved"], ["executed", "Executed"], ["rejected", "Rejected"], ["withdrawn", "Withdrawn"]] as const;
const SOURCE: Record<string, string> = { P08: "Negative keywords", P09: "Ad copy", P14: "Recommendation", P15: "Campaign builder", P20: "Experiment" };
const RISK: Record<string, string> = { low: "bg-ok/15 text-ok", medium: "bg-warn/15 text-warn", high: "bg-danger/15 text-danger" };
const btn = "rounded-md border border-line px-2.5 py-1 text-xs hover:bg-surface-2 disabled:opacity-50";
const humanize = (s: string) => s.replace(/_/g, " ");

function Val({ v }: { v: Json }) {
  if (Array.isArray(v)) {
    return <ul className="list-disc pl-4">{v.slice(0, 40).map((x, i) => <li key={i}><Val v={x} /></li>)}{v.length > 40 && <li className="text-muted">…and {v.length - 40} more</li>}</ul>;
  }
  if (v && typeof v === "object") {
    return <span>{Object.entries(v).map(([k, x]) => `${humanize(k)}: ${typeof x === "object" ? JSON.stringify(x) : String(x)}`).join(" · ")}</span>;
  }
  return <span>{v === null ? "—" : String(v)}</span>;
}

function Side({ title, data }: { title: string; data: Record<string, Json> }) {
  return (
    <div className="rounded-md bg-surface-2 p-3">
      <div className="mb-1 text-xs font-semibold uppercase text-muted">{title}</div>
      <dl className="grid gap-1 text-sm">
        {Object.entries(data).map(([k, v]) => <div key={k}><dt className="text-xs text-muted">{humanize(k)}</dt><dd><Val v={v} /></dd></div>)}
      </dl>
    </div>
  );
}

function ApprovalCard({ a, busy, onDecide }: { a: Approval; busy: boolean; onDecide: (a: Approval, d: string, note: string, confirm: string) => void }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [confirm, setConfirm] = useState("");
  const [detail, setDetail] = useState<Approval | null>(null);

  async function toggle() {
    setOpen((o) => !o);
    if (!detail) setDetail(await call<Approval>(`/${a.id}`).catch(() => null));
  }

  return (
    <li className="rounded-lg border border-line bg-surface">
      <button className="flex w-full flex-wrap items-start gap-2 p-3 text-left" onClick={toggle} aria-expanded={open}>
        <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-muted">{SOURCE[a.source_module] ?? a.source_module}</span>
        <span className="min-w-0 flex-1">
          <span className="font-medium">{a.title}</span>
          <span className="block text-xs text-muted">{humanize(a.change_type)} · requested {new Date(a.created_at).toLocaleString("en-AU")}{a.requested_by && <> by {a.requested_by}</>}</span>
        </span>
        {a.impact === "high" && <span className="rounded bg-danger/15 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-danger">high impact</span>}
        <span className={`rounded px-1.5 py-0.5 text-[10px] uppercase ${RISK[a.risk] ?? ""}`}>risk {a.risk}</span>
      </button>
      {open && (
        <div className="grid gap-3 border-t border-line px-3 pb-3 pt-2 text-sm">
          <div className="grid gap-3 md:grid-cols-2">
            <Side title="Before" data={a.before} />
            <Side title="After (proposed)" data={a.after} />
          </div>
          {a.evidence.length > 0 && (
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5 text-xs">
              {a.evidence.map(([k, v], i) => <Fragment key={i}><dt className="text-muted">{k}</dt><dd>{v}</dd></Fragment>)}
            </dl>
          )}
          {a.decision_note && <p className="text-xs"><span className="text-muted">Decision note:</span> {a.decision_note}</p>}
          {a.execution_result && <p className="text-xs"><span className="text-muted">Execution:</span> {a.execution_result}</p>}
          {(a.status === "pending" || a.status === "approved") && (
            <div className="grid gap-2 rounded-md border border-line p-3">
              <label className="text-xs text-muted">Note {a.status === "pending" && "(required to reject" + (a.impact === "high" ? "; also to approve your own request)" : ")")}
                <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000}
                  className="mt-1 w-full rounded-md border border-line bg-surface px-2 py-1 text-sm text-fg" />
              </label>
              {a.status === "pending" && a.confirm_required && (
                <label className="text-xs text-muted">High-impact change — type <b>{a.confirm_required}</b> to confirm
                  <input value={confirm} onChange={(e) => setConfirm(e.target.value)} maxLength={32}
                    className="mt-1 w-40 rounded-md border border-line bg-surface px-2 py-1 text-sm text-fg" />
                </label>
              )}
              <div className="flex flex-wrap gap-2">
                {a.status === "pending" && <>
                  <button className="rounded-md bg-accent px-3 py-1 text-xs font-medium text-white disabled:opacity-50" disabled={busy}
                    onClick={() => onDecide(a, "approve", note, confirm)}>Approve</button>
                  <button className={btn} disabled={busy} onClick={() => onDecide(a, "reject", note, "")}>Reject</button>
                </>}
                <button className={btn} disabled={busy} onClick={() => onDecide(a, "withdraw", note, "")}>Withdraw</button>
              </div>
              <p className="text-[11px] text-muted">Approving records your decision only. Nothing is sent to Google Ads — automatic execution (P17) is not built and the kill switch is on.</p>
            </div>
          )}
          {detail?.history && (
            <ol className="grid gap-0.5 text-xs text-muted">
              {detail.history.map((h, i) => <li key={i}>{new Date(h.at).toLocaleString("en-AU")} — <b className="text-fg">{h.event}</b>{h.by && <> by {h.by}</>}{h.note && <> · “{h.note}”</>}</li>)}
            </ol>
          )}
        </div>
      )}
    </li>
  );
}

export function ApprovalsPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [accId, setAccId] = useState<number | null>(null);
  const [tab, setTab] = useState<string>("pending");
  const [items, setItems] = useState<Approval[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    const a = await call<Account[]>("/accounts");
    setAccounts(a);
    const id = accId ?? a[0]?.id ?? null;
    if (id !== accId) setAccId(id);
    if (id) setItems(await call<Approval[]>(`/accounts/${id}?status=${tab}`));
  }, [accId, tab]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load on selection change
    load().catch((e) => {
      if ((e as { status?: number }).status === 401) router.replace("/login?next=/approvals");
      else setMsg({ ok: false, text: (e as Error).message });
    });
  }, [load, router]);

  async function act(label: string, fn: () => Promise<unknown>) {
    setBusy(label); setMsg(null);
    try { await fn(); await load(); }
    catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
    finally { setBusy(null); }
  }

  const sync = () => act("sync", async () => {
    const r = await call<{ created: number; withdrawn: number }>(`/accounts/${accId}/sync`, { method: "POST" });
    setMsg({ ok: true, text: `${r.created} new request(s) · ${r.withdrawn} withdrawn because the source is no longer approved.` });
  });
  const decide = (a: Approval, decision: string, note: string, confirm: string) => act(`d${a.id}`, async () => {
    await call(`/${a.id}/decision`, { method: "POST", body: JSON.stringify({ decision, note: note || null, confirm: confirm || null }) });
    setMsg({ ok: true, text: `“${a.title}” — ${decision === "approve" ? "approved" : decision === "reject" ? "rejected" : "withdrawn"}.` });
  });
  const counts = accounts?.find((a) => a.id === accId)?.counts ?? {};

  return (
    <>
      <PageHeader title="Approval Center" moduleId="P16">
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/execution" className="text-xs text-accent underline">Send approved changes to Google Ads →</Link>
          {accounts && accounts.length > 1 && (
            <select aria-label="Ads account" className="rounded-md border border-line bg-surface px-2 py-1 text-sm" value={accId ?? ""} onChange={(e) => setAccId(Number(e.target.value))}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name || a.customer_id}</option>)}
            </select>
          )}
          <button onClick={sync} disabled={!accId || !!busy} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
            {busy === "sync" ? "Collecting…" : "Sync queue"}
          </button>
        </div>
      </PageHeader>
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}
      <p className="mb-4 text-sm text-muted">
        “Sync queue” collects changes you already accepted elsewhere — accepted negatives (Search terms), approved ads (Ads &amp; Assets),
        approved campaign drafts (Campaign Builder) and accepted recommendations that change Google Ads. Decide each one here.
      </p>
      {accounts && !accounts.length && <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">Connect and sync a Google Ads account first.</p>}

      <div role="tablist" className="mb-3 flex w-fit flex-wrap overflow-hidden rounded-md border border-line">
        {TABS.map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`px-3 py-1 text-sm ${tab === k ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"}`}>
            {l}{counts[k] ? <span className="ml-1 tabular-nums text-muted">({counts[k]})</span> : null}
          </button>
        ))}
      </div>
      {accId && !items.length && (
        <p className="rounded-lg border border-dashed border-line bg-surface p-6 text-center text-sm text-muted">
          {tab === "pending" ? "Nothing waiting. Approve something in another module, then click “Sync queue”." : "Nothing here."}
        </p>
      )}
      <ol className="grid gap-2">
        {items.map((a) => <ApprovalCard key={a.id} a={a} busy={!!busy} onDecide={decide} />)}
      </ol>
    </>
  );
}
