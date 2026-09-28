"use client";
// P21 — edit versioned business rules (global scope). One item per line.
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { API_BASE, PageHeader } from "@/shell";

type Rules = {
  services: string[]; locations: string[]; other_locations: string[]; excluded_terms: string[];
  competitor_terms: string[]; brand_terms: string[]; min_spend_for_negative: number;
  min_clicks_for_negative: number; target_cost_per_conversion: number | null; notes: string;
};
type Current = { scope: string; version: number; is_default: boolean; rules: Rules; updated_at: string | null; updated_by: string | null; note: string };
type Version = { version: number; note: string; created_by_email: string | null; created_at: string };

const BASE = `${API_BASE}/api/v1/business-rules`;
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { ...init, credentials: "include", headers: { "content-type": "application/json" } });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(body?.error?.message ?? `HTTP ${r.status}`), { status: r.status });
  return body as T;
}

const LISTS: { key: keyof Rules; label: string; help: string }[] = [
  { key: "services", label: "Services you offer", help: "Searches containing these are relevant (e.g. airport transfer, wedding car)." },
  { key: "locations", label: "Areas you serve", help: "Suburbs, cities, airports, venues." },
  { key: "excluded_terms", label: "Searches you never want", help: "Any search containing one of these becomes a negative-keyword suggestion (e.g. jobs, cheap, uber)." },
  { key: "other_locations", label: "Places you don't serve", help: "Searches naming these (without one of your areas) are suggested as negatives." },
  { key: "competitor_terms", label: "Competitor names", help: "Flagged as competitor searches (not auto-negated)." },
  { key: "brand_terms", label: "Your brand names", help: "Searches for your own brand — always treated as high value." },
];

export function RulesPage() {
  const router = useRouter();
  const [cur, setCur] = useState<Current | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [nums, setNums] = useState({ min_spend_for_negative: "20", min_clicks_for_negative: "5", target_cost_per_conversion: "" });
  const [note, setNote] = useState("");
  const [versions, setVersions] = useState<Version[]>([]);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const apply = useCallback((c: Current) => {
    setCur(c);
    setDraft(Object.fromEntries(LISTS.map((l) => [l.key, (c.rules[l.key] as string[]).join("\n")])));
    setNums({
      min_spend_for_negative: String(c.rules.min_spend_for_negative),
      min_clicks_for_negative: String(c.rules.min_clicks_for_negative),
      target_cost_per_conversion: c.rules.target_cost_per_conversion === null ? "" : String(c.rules.target_cost_per_conversion),
    });
  }, []);

  const load = useCallback(async () => {
    try {
      apply(await call<Current>(""));
      setVersions(await call<Version[]>("/versions"));
    } catch (e) {
      if ((e as { status?: number }).status === 401) router.replace("/login?next=/business-rules");
      else setMsg({ ok: false, text: (e as Error).message });
    }
  }, [apply, router]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load
    load();
  }, [load]);

  async function save() {
    if (!cur) return;
    setBusy(true);
    setMsg(null);
    try {
      const rules: Rules = {
        ...cur.rules,
        ...Object.fromEntries(LISTS.map((l) => [l.key, (draft[l.key] ?? "").split("\n").map((s) => s.trim()).filter(Boolean)])),
        min_spend_for_negative: Number(nums.min_spend_for_negative) || 0,
        min_clicks_for_negative: Math.max(1, Math.round(Number(nums.min_clicks_for_negative) || 1)),
        target_cost_per_conversion: nums.target_cost_per_conversion === "" ? null : Number(nums.target_cost_per_conversion),
      };
      const c = await call<Current>("", { method: "PUT", body: JSON.stringify({ rules, note }) });
      apply(c);
      setVersions(await call<Version[]>("/versions"));
      setNote("");
      setMsg({ ok: true, text: c.version === cur.version ? "No changes to save." : `Saved as version ${c.version}. Re-run keyword analysis to use the new rules.` });
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }

  async function restore(v: number) {
    if (!confirm(`Restore version ${v}? This creates a new version with those rules.`)) return;
    try {
      apply(await call<Current>(`/versions/${v}/restore`, { method: "POST" }));
      setVersions(await call<Version[]>("/versions"));
      setMsg({ ok: true, text: `Restored version ${v}.` });
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  }

  const input = "w-full rounded-md border border-line bg-surface px-2 py-1.5 text-sm";
  return (
    <>
      <PageHeader title="Business Rules" moduleId="P21">
        <button onClick={save} disabled={busy || !cur} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">
          {busy ? "Saving…" : "Save rules"}
        </button>
      </PageHeader>
      {cur && (
        <p className="-mt-3 mb-4 text-xs text-muted">
          {cur.is_default ? "Using built-in chauffeur defaults — edit and save to make them yours." :
            `Version ${cur.version} · saved ${cur.updated_at ? new Date(cur.updated_at).toLocaleString("en-AU") : ""} by ${cur.updated_by ?? "?"}`}
        </p>
      )}
      {msg && <div role="status" className={`mb-4 rounded-md border px-3 py-2 text-sm ${msg.ok ? "border-ok/30 bg-ok/10 text-ok" : "border-danger/30 bg-danger/10 text-danger"}`}>{msg.text}</div>}

      {cur && (
        <div className="grid gap-4 lg:grid-cols-2">
          {LISTS.map((l) => (
            <label key={l.key} className="flex flex-col gap-1 rounded-lg border border-line bg-surface p-4">
              <span className="font-semibold">{l.label} <span className="text-xs font-normal text-muted">({(draft[l.key] ?? "").split("\n").filter((s) => s.trim()).length})</span></span>
              <span className="text-xs text-muted">{l.help} One per line.</span>
              <textarea className={`${input} mt-1 h-40 font-mono text-xs`} value={draft[l.key] ?? ""}
                onChange={(e) => setDraft({ ...draft, [l.key]: e.target.value })} />
            </label>
          ))}
          <section className="rounded-lg border border-line bg-surface p-4 lg:col-span-2">
            <h2 className="mb-2 font-semibold">Thresholds</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="text-sm">Min spend before suggesting a negative ($)
                <input className={`${input} mt-1`} type="number" min={0} step="1" value={nums.min_spend_for_negative} onChange={(e) => setNums({ ...nums, min_spend_for_negative: e.target.value })} />
              </label>
              <label className="text-sm">Min clicks before suggesting a negative
                <input className={`${input} mt-1`} type="number" min={1} step="1" value={nums.min_clicks_for_negative} onChange={(e) => setNums({ ...nums, min_clicks_for_negative: e.target.value })} />
              </label>
              <label className="text-sm">Target cost per conversion ($, optional)
                <input className={`${input} mt-1`} type="number" min={0} step="1" value={nums.target_cost_per_conversion} onChange={(e) => setNums({ ...nums, target_cost_per_conversion: e.target.value })} />
              </label>
            </div>
            <label className="mt-3 block text-sm">What changed? (saved with this version)
              <input className={`${input} mt-1`} value={note} maxLength={2000} onChange={(e) => setNote(e.target.value)} placeholder="e.g. added Geelong, removed 'bus'" />
            </label>
          </section>
          <section className="rounded-lg border border-line bg-surface p-4 lg:col-span-2">
            <h2 className="mb-2 font-semibold">Version history</h2>
            {versions.length === 0 ? <p className="text-sm text-muted">No saved versions yet.</p> : (
              <ul className="divide-y divide-line text-sm">
                {versions.map((v) => (
                  <li key={v.version} className="flex flex-wrap items-center gap-3 py-1.5">
                    <span className="font-medium">v{v.version}</span>
                    <span className="text-muted">{new Date(v.created_at).toLocaleString("en-AU")} · {v.created_by_email}</span>
                    <span>{v.note}</span>
                    {v.version !== cur.version && <button className="ml-auto text-accent" onClick={() => restore(v.version)}>Restore</button>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </>
  );
}
