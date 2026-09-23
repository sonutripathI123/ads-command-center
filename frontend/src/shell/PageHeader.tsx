import type { ReactNode } from "react";

export function PageHeader({ title, moduleId, children }: { title: string; moduleId: string; children?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <div className="text-xs font-medium uppercase tracking-wider text-muted">{moduleId}</div>
        <h1 className="text-2xl font-semibold">{title}</h1>
      </div>
      {children}
    </div>
  );
}
