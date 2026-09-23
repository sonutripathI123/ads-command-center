"use client";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useFoundation, type Health, type ModuleInfo } from "./api";
import { ModuleStatusProvider } from "./ModuleStatus";
import { ScopeProvider } from "./ScopeContext";
import { ScopeSelector } from "./ScopeSelector";
import { Sidebar } from "./Sidebar";
import { AlertStrip, StatusPills } from "./StatusBar";

type AppShellProps = {
  children: ReactNode;
  /** Rendered at the right of the top bar (e.g. P02 user menu). Supplied by app/layout.tsx. */
  headerRight?: ReactNode;
  /** Routes rendered without sidebar/top bar (e.g. P02 /login). */
  bareRoutes?: string[];
};

export function AppShell({ children, headerRight, bareRoutes = [] }: AppShellProps) {
  const pathname = usePathname();
  const health = useFoundation<Health>("health");
  const modules = useFoundation<ModuleInfo[]>("modules");
  const [menuOpen, setMenuOpen] = useState(false);
  const statusById = Object.fromEntries((modules.data ?? []).map((m) => [m.id, m.status]));

  if (bareRoutes.includes(pathname)) {
    return <main className="min-h-screen px-4 py-5">{children}</main>;
  }

  return (
    <ScopeProvider>
      <ModuleStatusProvider value={{ modules: modules.data, loading: modules.loading }}>
        <div className="flex min-h-screen">
          <aside
            className={`fixed inset-y-0 left-0 z-30 w-64 overflow-y-auto border-r border-line bg-surface transition-transform lg:static lg:translate-x-0 ${
              menuOpen ? "translate-x-0" : "-translate-x-full"
            }`}
          >
            <Sidebar statusById={statusById} onNavigate={() => setMenuOpen(false)} />
          </aside>
          {menuOpen && <div className="fixed inset-0 z-20 bg-black/30 lg:hidden" onClick={() => setMenuOpen(false)} />}

          <div className="flex min-w-0 flex-1 flex-col">
            <header className="sticky top-0 z-10 flex flex-wrap items-center gap-3 border-b border-line bg-surface/95 px-4 py-2.5 backdrop-blur sm:px-6">
              <button
                className="rounded-md border border-line px-2 py-1 text-sm lg:hidden"
                onClick={() => setMenuOpen(true)}
                aria-label="Open navigation"
              >
                ☰
              </button>
              <ScopeSelector />
              <div className="ml-auto flex flex-wrap items-center gap-2">
                <StatusPills health={health.data} error={health.error} loading={health.loading} />
                {headerRight}
              </div>
            </header>
            <AlertStrip error={health.error} />
            <main className="flex-1 px-4 py-5 sm:px-6">{children}</main>
          </div>
        </div>
      </ModuleStatusProvider>
    </ScopeProvider>
  );
}
