"use client";
// P01 — client-side composition of the shell with module-provided pieces (functions can't cross the
// server→client boundary from layout.tsx). The shell itself still imports no feature module.
import type { ReactNode } from "react";
import { PUBLIC_PATHS, UserMenu } from "@/modules/auth";
import { SyncAllButton } from "@/modules/data-sync";
import { loadScope } from "@/modules/websites";
import { AppShell } from "@/shell/AppShell";

export function ShellFrame({ children }: { children: ReactNode }) {
  return (
    <AppShell headerRight={<div className="flex items-center gap-3"><SyncAllButton /><UserMenu /></div>} bareRoutes={PUBLIC_PATHS} scopeLoader={loadScope}>
      {children}
    </AppShell>
  );
}
