"use client";
import { useState } from "react";
import { authApi } from "./api";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await authApi.login(email, password);
      const next = new URLSearchParams(window.location.search).get("next");
      window.location.assign(next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
      setBusy(false);
    }
  }

  const input = "w-full rounded-md border border-line bg-surface px-3 py-2 text-sm";
  return (
    <form onSubmit={submit} className="mx-auto mt-10 flex w-full max-w-sm flex-col gap-3 rounded-lg border border-line bg-surface p-6">
      <div>
        <div className="text-xs font-medium uppercase tracking-wider text-muted">P02</div>
        <h1 className="text-xl font-semibold">Sign in</h1>
      </div>
      <label className="flex flex-col gap-1 text-sm">
        Email
        <input className={input} type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Password
        <input className={input} type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </label>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      <button disabled={busy} className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white disabled:opacity-60">
        {busy ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
