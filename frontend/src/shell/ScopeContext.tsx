"use client";
// P01 — selected website / ads account, shared with every module page via useScope().
// Persisted in localStorage through a tiny external store (server render always uses "all").
import { createContext, useContext, useSyncExternalStore, type ReactNode } from "react";
import { MOCK_ADS_ACCOUNTS, MOCK_WEBSITES, type AdsAccount, type Website } from "./mock/scope";

const ALL = "all";
const STORAGE_KEY = "p01.scope";

type Selection = { websiteId: string; adsAccountId: string };
const DEFAULT: Selection = { websiteId: ALL, adsAccountId: ALL };

let current: Selection | null = null;
const listeners = new Set<() => void>();

function read(): Selection {
  if (current) return current;
  try {
    current = { ...DEFAULT, ...JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") };
  } catch {
    current = DEFAULT;
  }
  return current!;
}

function write(patch: Partial<Selection>) {
  current = { ...read(), ...patch };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
  } catch {
    /* storage unavailable — selection lasts for this tab only */
  }
  listeners.forEach((l) => l());
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

type Scope = Selection & {
  websites: Website[];
  adsAccounts: AdsAccount[];
  setWebsiteId: (id: string) => void;
  setAdsAccountId: (id: string) => void;
};

const ScopeCtx = createContext<Scope | null>(null);

export function ScopeProvider({ children }: { children: ReactNode }) {
  const sel = useSyncExternalStore(subscribe, read, () => DEFAULT);
  return (
    <ScopeCtx.Provider
      value={{
        ...sel,
        websites: MOCK_WEBSITES,
        adsAccounts: MOCK_ADS_ACCOUNTS,
        setWebsiteId: (websiteId) => write({ websiteId }),
        setAdsAccountId: (adsAccountId) => write({ adsAccountId }),
      }}
    >
      {children}
    </ScopeCtx.Provider>
  );
}

export function useScope(): Scope {
  const ctx = useContext(ScopeCtx);
  if (!ctx) throw new Error("useScope must be used inside <ScopeProvider>");
  return ctx;
}

export const SCOPE_ALL = ALL;
