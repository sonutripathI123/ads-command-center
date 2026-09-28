"use client";
// P03 — list of websites + add form.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/shell";
import { sitesApi, type Meta, type Website } from "./api";
import { WebsiteForm } from "./WebsiteForm";

export function WebsitesPage() {
  const router = useRouter();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [sites, setSites] = useState<Website[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, s] = await Promise.all([sitesApi.meta(), sitesApi.list()]);
      setMeta(m);
      setSites(s);
    } catch (e) {
      if ((e as { status?: number }).status === 401) router.replace("/login?next=/websites");
      else setError((e as Error).message);
    }
  }, [router]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load
    load();
  }, [load]);

  return (
    <>
      <PageHeader title="Websites" moduleId="P03">
        {!adding && <button onClick={() => setAdding(true)} className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white">+ Add website</button>}
      </PageHeader>
      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {adding && meta && (
        <div className="mb-4">
          <WebsiteForm meta={meta} onCancel={() => setAdding(false)} onSave={async (w) => {
            const created = await sitesApi.create(w);
            setAdding(false);
            router.push(`/websites/${created.id}`);
          }} />
        </div>
      )}
      {sites && sites.length === 0 && !adding && (
        <div className="rounded-lg border border-dashed border-line bg-surface p-8 text-center">
          <p className="font-medium">No websites yet</p>
          <p className="mt-1 text-sm text-muted">Add each of your sites and link it to its Google Ads account.</p>
          <button onClick={() => setAdding(true)} className="mt-3 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white">+ Add your first website</button>
        </div>
      )}
      {sites && sites.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2">
          {sites.map((s) => (
            <Link key={s.id} href={`/websites/${s.id}`} className="rounded-lg border border-line bg-surface p-4 hover:border-accent/50">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-semibold">{s.name}</div>
                  <div className="text-sm text-muted">{s.domain}</div>
                </div>
                <span className="text-xs text-muted">{[s.primary_service, s.location].filter(Boolean).join(" · ")}</span>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <dt className="text-muted">Google Ads</dt><dd>{s.ads_customer_id ? s.ads_customer_id.replace(/^(\d{3})(\d{3})(\d{4})$/, "$1-$2-$3") : <span className="text-warn">not linked</span>}</dd>
                <dt className="text-muted">GA4</dt><dd>{s.ga4_property_id ?? <span className="text-muted">—</span>}</dd>
                <dt className="text-muted">Pages scanned</dt><dd>{s.pages}{s.pages ? ` (${s.pages_with_issues} with issues)` : ""}</dd>
                <dt className="text-muted">Last scan</dt><dd>{s.last_crawl ? `${new Date(s.last_crawl.started_at).toLocaleDateString("en-AU")} · ${s.last_crawl.status}` : "never"}</dd>
              </dl>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
