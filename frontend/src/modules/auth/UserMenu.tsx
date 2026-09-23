"use client";
// P02 — top-bar user menu, injected into the P01 shell via app/layout.tsx (headerRight slot).
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { authApi, type Me } from "./api";

export function UserMenu() {
  const [me, setMe] = useState<Me | null>(null);
  const router = useRouter();

  useEffect(() => {
    authApi.me().then(setMe).catch(() => setMe(null));
  }, []);

  async function logout() {
    await authApi.logout().catch(() => undefined);
    router.replace("/login");
    router.refresh();
  }

  if (!me) return null;
  return (
    <div className="flex items-center gap-2 text-sm">
      <Link href="/account" className="rounded-md px-2 py-1 hover:bg-surface-2" title={`${me.email} · ${me.role}`}>
        {me.name || me.email}
      </Link>
      <button onClick={logout} className="rounded-md border border-line px-2 py-1 text-xs">Sign out</button>
    </div>
  );
}
