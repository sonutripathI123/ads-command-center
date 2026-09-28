"use client";
// P03 — add / edit a website.
import { useState } from "react";
import type { Meta, Website, WebsiteInput } from "./api";

const SERVICES = ["Chauffeur", "Corporate", "Airport transfer", "Wedding", "Events / formals", "Cruise transfer", "Tours", "Limousine"];
const ZONES = ["Australia/Melbourne", "Australia/Sydney", "Australia/Brisbane", "Australia/Adelaide", "Australia/Perth", "Australia/Hobart"];

export function WebsiteForm({ meta, initial, onSave, onCancel }: {
  meta: Meta; initial?: Website; onSave: (w: WebsiteInput) => Promise<void>; onCancel: () => void;
}) {
  const [f, setF] = useState<WebsiteInput>({
    name: initial?.name ?? "", domain: initial?.base_url ?? "", primary_service: initial?.primary_service ?? "",
    location: initial?.location ?? "", time_zone: initial?.time_zone ?? "Australia/Melbourne",
    ads_account_id: initial?.ads_account_id ?? null, ga4_property_id: initial?.ga4_property_id ?? "",
    gsc_site_url: initial?.gsc_site_url ?? "", notes: initial?.notes ?? "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const input = "w-full rounded-md border border-line bg-surface px-2 py-1.5 text-sm";
  const set = (k: keyof WebsiteInput) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setF({ ...f, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSave({ ...f, ga4_property_id: f.ga4_property_id?.trim() || null, gsc_site_url: f.gsc_site_url?.trim() || null });
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-lg border border-accent/40 bg-surface p-4">
      <h2 className="mb-3 font-semibold">{initial ? `Edit ${initial.name}` : "Add website"}</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">Website name *
          <input className={`${input} mt-1`} required value={f.name} onChange={set("name")} placeholder="Corporate Cars Melbourne" />
        </label>
        <label className="text-sm">Domain *
          <input className={`${input} mt-1`} required disabled={!!initial} value={f.domain} onChange={set("domain")} placeholder="https://corporatecarsmelbourne.com.au" />
        </label>
        <label className="text-sm">Main service
          <input className={`${input} mt-1`} list="p03-services" value={f.primary_service} onChange={set("primary_service")} placeholder="Corporate" />
          <datalist id="p03-services">{SERVICES.map((s) => <option key={s} value={s} />)}</datalist>
        </label>
        <label className="text-sm">City / area
          <input className={`${input} mt-1`} value={f.location} onChange={set("location")} placeholder="Melbourne" />
        </label>
        <label className="text-sm">Google Ads account
          <select className={`${input} mt-1`} value={f.ads_account_id ?? ""} onChange={(e) => setF({ ...f, ads_account_id: e.target.value ? Number(e.target.value) : null })}>
            <option value="">— not linked —</option>
            {meta.ads_accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name || "Account"} ({a.customer_id.replace(/^(\d{3})(\d{3})(\d{4})$/, "$1-$2-$3")})</option>
            ))}
          </select>
        </label>
        <label className="text-sm">Time zone
          <select className={`${input} mt-1`} value={f.time_zone} onChange={set("time_zone")}>{ZONES.map((z) => <option key={z}>{z}</option>)}</select>
        </label>
        <label className="text-sm">GA4 property ID <span className="text-muted">(optional, digits — GA4 → Admin → Property details)</span>
          <input className={`${input} mt-1`} inputMode="numeric" value={f.ga4_property_id ?? ""} onChange={set("ga4_property_id")} placeholder="550393874" />
        </label>
        <label className="text-sm">Search Console property <span className="text-muted">(optional)</span>
          <input className={`${input} mt-1`} value={f.gsc_site_url ?? ""} onChange={set("gsc_site_url")} placeholder="https://corporatecarsmelbourne.com.au/" />
        </label>
        <label className="text-sm sm:col-span-2">Notes
          <textarea className={`${input} mt-1 h-16`} value={f.notes} onChange={set("notes")} />
        </label>
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-danger">{error}</p>}
      <div className="mt-3 flex gap-2">
        <button disabled={busy} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">{busy ? "Saving…" : "Save"}</button>
        <button type="button" onClick={onCancel} className="rounded-md border border-line px-3 py-1.5 text-sm">Cancel</button>
      </div>
    </form>
  );
}
