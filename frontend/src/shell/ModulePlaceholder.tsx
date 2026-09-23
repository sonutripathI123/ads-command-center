"use client";
import { useModuleStatus } from "./ModuleStatus";
import type { NavItem } from "./nav";
import { PageHeader } from "./PageHeader";
import { SCOPE_ALL, useScope } from "./ScopeContext";

export function ModulePlaceholder({ item }: { item: NavItem }) {
  const { modules } = useModuleStatus();
  const { websites, websiteId } = useScope();
  const mod = modules?.find((m) => m.id === item.moduleId);
  const site = websiteId === SCOPE_ALL ? "All websites" : websites.find((w) => w.id === websiteId)?.name;

  return (
    <>
      <PageHeader title={item.label} moduleId={item.moduleId} />
      <div className="rounded-lg border border-dashed border-line bg-surface p-8 text-center">
        <p className="font-medium">Not built yet</p>
        <p className="mt-1 text-sm text-muted">
          This section is owned by {item.moduleId}
          {mod ? ` — ${mod.name}` : ""} (status: {mod?.status ?? "planned"}).
        </p>
        <p className="mt-3 text-xs text-muted">Scope: {site}</p>
      </div>
    </>
  );
}
