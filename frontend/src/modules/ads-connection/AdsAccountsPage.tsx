"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/shell";
import { adsApi, ApiError, formatCid, type Discovered, type Status } from "./api";

const card = "rounded-lg border border-line bg-surface p-4";
const btn = "rounded-md border border-line px-3 py-1.5 text-sm hover:bg-surface-2 disabled:opacity-50";
const primary = "rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50";

export function AdsAccountsPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [status, setStatus] = useState<Status | null>(null);
  const [discovered, setDiscovered] = useState<{ connectionId: number; items: Discovered[] } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ tone: "ok" | "danger"; text: string } | null>(() => {
    if (params.get("connected")) return { tone: "ok", text: "Google account connected. Now find and add your ads accounts below." };
    if (params.get("error")) return { tone: "danger", text: params.get("error") ?? "" };
    return null;
  });

  const load = useCallback(async () => {
    try {
      setStatus(await adsApi.status());
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) router.replace("/login?next=/ads-accounts");
      else setMsg({ tone: "danger", text: (e as Error).message });
    }
  }, [router]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load
    load();
  }, [load]);

  async function run(label: string, fn: () => Promise<unknown>, ok?: string) {
    setBusy(label);
    setMsg(null);
    try {
      await fn();
      if (ok) setMsg({ tone: "ok", text: ok });
      await load();
    } catch (e) {
      setMsg({ tone: "danger", text: (e as Error).message });
    } finally {
      setBusy(null);
    }
  }

  const ready = status?.oauth_client_configured && status?.developer_token_configured;
  const activeConns = status?.connections.filter((c) => c.status !== "revoked") ?? [];

  return (
    <>
      <PageHeader title="Ads Accounts" moduleId="P04">
        <a href={ready ? adsApi.connectUrl : undefined} aria-disabled={!ready}
          className={`${primary} ${ready ? "" : "pointer-events-none opacity-50"}`}>
          Connect Google Ads
        </a>
      </PageHeader>

      {msg && (
        <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${
          msg.tone === "ok" ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>
          {msg.text}
        </div>
      )}

      {status && (
        <section className={card}>
          <h2 className="mb-2 font-semibold">Setup</h2>
          <ul className="flex flex-col gap-1 text-sm">
            <Check ok={status.oauth_client_configured} label="Google OAuth client (GOOGLE_OAUTH_CLIENT_ID / SECRET)" />
            <Check ok={status.developer_token_configured} label="Google Ads developer token" />
            <li className="text-muted">API {status.api_version} · read-only · redirect URI <code className="text-xs">{status.redirect_uri}</code></li>
          </ul>
        </section>
      )}

      <section className={`${card} mt-4`}>
        <h2 className="mb-2 font-semibold">Google connections</h2>
        {activeConns.length === 0 ? (
          <p className="text-sm text-muted">No Google account connected yet. Click “Connect Google Ads” and approve access.</p>
        ) : (
          <ul className="flex flex-col divide-y divide-line">
            {activeConns.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-3 py-2 text-sm">
                <span className="font-medium">{c.google_email ?? `Connection #${c.id}`}</span>
                <span className={c.status === "active" ? "text-ok" : "text-danger"}>{c.status}</span>
                {c.last_error && <span className="text-xs text-danger">{c.last_error}</span>}
                <span className="ml-auto flex gap-2">
                  <button className={btn} disabled={!!busy} onClick={() => run(`check${c.id}`, () => adsApi.check(c.id), "Connection is working.")}>
                    {busy === `check${c.id}` ? "Checking…" : "Test"}
                  </button>
                  <button className={btn} disabled={!!busy}
                    onClick={() => run(`disc${c.id}`, async () => setDiscovered({ connectionId: c.id, items: await adsApi.discover(c.id) }))}>
                    {busy === `disc${c.id}` ? "Searching…" : "Find accounts"}
                  </button>
                  <button className={btn} disabled={!!busy}
                    onClick={() => confirm("Disconnect this Google account? Its ads accounts will be disabled.") &&
                      run(`dc${c.id}`, () => adsApi.disconnect(c.id), "Disconnected.")}>
                    Disconnect
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {discovered && (
        <section className={`${card} mt-4`}>
          <h2 className="mb-2 font-semibold">Accounts this Google login can read</h2>
          <AccountTable rows={discovered.items.map((d) => ({
            key: d.customer_id, name: d.descriptive_name, cid: d.customer_id, meta: `${d.currency_code ?? ""} · ${d.time_zone ?? ""}`,
            tag: d.is_manager ? "manager" : d.login_customer_id ? `via ${formatCid(d.login_customer_id)}` : "direct",
            action: d.is_manager ? <span className="text-xs text-muted">manager — add its accounts</span>
              : d.already_added ? <span className="text-xs text-ok">added</span>
              : <button className={primary} disabled={!!busy}
                  onClick={() => run(`add${d.customer_id}`, async () => {
                    await adsApi.addAccount(discovered.connectionId, d.customer_id, d.login_customer_id);
                    setDiscovered({ ...discovered, items: discovered.items.map((x) => x.customer_id === d.customer_id ? { ...x, already_added: true } : x) });
                  }, `${d.descriptive_name} added.`)}>Add</button>,
          }))} />
        </section>
      )}

      <section className={`${card} mt-4`}>
        <h2 className="mb-2 font-semibold">Accounts in this dashboard</h2>
        {!status?.accounts.length ? <p className="text-sm text-muted">None yet.</p> : (
          <AccountTable rows={status.accounts.map((a) => ({
            key: String(a.id), name: a.descriptive_name, cid: a.customer_id, meta: `${a.currency_code ?? ""} · ${a.time_zone ?? ""}`,
            tag: a.status,
            action: <button className={btn} disabled={!!busy}
              onClick={() => run(`st${a.id}`, () => adsApi.setStatus(a.id, a.status === "active" ? "disabled" : "active"))}>
              {a.status === "active" ? "Disable" : "Enable"}</button>,
          }))} />
        )}
        <p className="mt-3 text-xs text-muted">Read-only access. This dashboard cannot change anything in Google Ads.</p>
      </section>
    </>
  );
}

function Check({ ok, label }: { ok: boolean; label: string }) {
  return <li className={ok ? "text-ok" : "text-danger"}>{ok ? "✓" : "✗"} <span className="text-fg">{label}</span>{!ok && " — add to backend/.env"}</li>;
}

type Row = { key: string; name: string; cid: string; meta: string; tag: string; action: React.ReactNode };

function AccountTable({ rows }: { rows: Row[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-muted">
          <tr><th className="py-1 pr-4 font-medium">Account</th><th className="pr-4 font-medium">Customer ID</th><th className="pr-4 font-medium">Currency · TZ</th><th className="pr-4 font-medium">Type</th><th /></tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((r) => (
            <tr key={r.key}>
              <td className="py-1.5 pr-4">{r.name || "—"}</td>
              <td className="pr-4 font-mono text-xs">{formatCid(r.cid)}</td>
              <td className="pr-4 text-muted">{r.meta}</td>
              <td className="pr-4 text-muted">{r.tag}</td>
              <td className="text-right">{r.action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
