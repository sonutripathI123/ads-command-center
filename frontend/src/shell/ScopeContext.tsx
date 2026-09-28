"use client";
// P01 — selected website / ads account, shared with every module page via useScope().
// Selection is persisted in localStorage through a tiny external store (server render always uses "all").
// The lists come from a loader passed in by app/ShellFrame.tsx (P03 websites + linked ads accounts);
// the shell itself never calls a module API.
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import type { AdsAccount, ScopeData, ScopeLoader, Website } from "./scope-types";

const ALL = "all";
const STORAGE_KEY = "p01.scope";
const EMPTY: ScopeData = { websites: [], adsAccounts: [] };

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
  loaded: boolean;
  setWebsiteId: (id: string) => void;
  setAdsAccountId: (id: string) => void;
};

const ScopeCtx = createContext<Scope | null>(null);

export function ScopeProvider({ children, loader }: { children: ReactNode; loader?: ScopeLoader }) {
  const sel = useSyncExternalStore(subscribe, read, () => DEFAULT);
  const pathname = usePathname();
  const [data, setData] = useState<ScopeData | null>(null);

  useEffect(() => {
    // Re-load on navigation so a website added on /websites shows up in the selector.
    let live = true;
    (loader ? loader() : Promise.resolve(EMPTY)).then((d) => live && setData(d)).catch(() => live && setData(EMPTY));
    return () => {
      live = false;
    };
  }, [loader, pathname]);

  const lists = data ?? EMPTY;
  // A remembered selection that no longer exists falls back to "all".
  const websiteId = sel.websiteId === ALL || lists.websites.some((w) => w.id === sel.websiteId) || !data ? sel.websiteId : ALL;
  const adsAccountId = sel.adsAccountId === ALL || lists.adsAccounts.some((a) => a.id === sel.adsAccountId) || !data ? sel.adsAccountId : ALL;

  return (
    <ScopeCtx.Provider
      value={{
        websiteId, adsAccountId, websites: lists.websites, adsAccounts: lists.adsAccounts, loaded: data !== null,
        setWebsiteId: (id) => write({ websiteId: id }),
        setAdsAccountId: (id) => write({ adsAccountId: id }),
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
