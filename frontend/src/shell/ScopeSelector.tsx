"use client";
import { SCOPE_ALL, useScope } from "./ScopeContext";

const selectCls = "rounded-md border border-line bg-surface px-2 py-1.5 text-sm max-w-[14rem]";

export function ScopeSelector() {
  const { websites, adsAccounts, websiteId, adsAccountId, setWebsiteId, setAdsAccountId } = useScope();
  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="sr-only" htmlFor="scope-website">Website</label>
      <select id="scope-website" className={selectCls} value={websiteId} onChange={(e) => setWebsiteId(e.target.value)}>
        <option value={SCOPE_ALL}>All websites ({websites.length})</option>
        {websites.map((w) => (
          <option key={w.id} value={w.id}>{w.name}{w.location ? ` — ${w.location}` : ""}</option>
        ))}
      </select>
      <label className="sr-only" htmlFor="scope-account">Ads account</label>
      <select id="scope-account" className={selectCls} value={adsAccountId} onChange={(e) => setAdsAccountId(e.target.value)}>
        <option value={SCOPE_ALL}>All ads accounts</option>
        {adsAccounts.map((a) => (
          <option key={a.id} value={a.id}>{a.name || "Account"} ({a.customerId.replace(/^(\d{3})(\d{3})(\d{4})$/, "$1-$2-$3")})</option>
        ))}
      </select>
    </div>
  );
}
