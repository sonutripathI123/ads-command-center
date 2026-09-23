"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/shell";
import { ApiError, authApi, type Me, type UserRow } from "./api";

export function AccountPanel() {
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    authApi.me().then(setMe).catch((e: ApiError) => {
      if (e.status === 401) router.replace("/login?next=/account");
      else setError(e.message);
    });
  }, [router]);

  async function logout() {
    await authApi.logout().catch(() => undefined);
    router.replace("/login");
    router.refresh();
  }

  return (
    <>
      <PageHeader title="Account" moduleId="P02">
        {me && <button onClick={logout} className="rounded-md border border-line px-3 py-1.5 text-sm">Sign out</button>}
      </PageHeader>
      {error && <p className="text-sm text-danger">{error}</p>}
      {me && (
        <section className="rounded-lg border border-line bg-surface p-4">
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
            <dt className="text-muted">Name</dt><dd>{me.name || "—"}</dd>
            <dt className="text-muted">Email</dt><dd>{me.email}</dd>
            <dt className="text-muted">Role</dt><dd>{me.role}</dd>
            <dt className="text-muted">Permissions</dt><dd>{me.permissions.join(", ")}</dd>
            <dt className="text-muted">Google Ads execute</dt>
            <dd>{me.permissions.includes("execute") ? "granted" : "not granted (default)"}</dd>
          </dl>
        </section>
      )}
      {me?.permissions.includes("admin") && <UsersAdmin selfId={me.id} />}
    </>
  );
}

function UsersAdmin({ selfId }: { selfId: number }) {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [form, setForm] = useState({ email: "", name: "", role: "viewer", password: "" });

  const load = useCallback(async () => {
    try {
      const [u, r] = await Promise.all([authApi.users(), authApi.roles()]);
      setUsers(u);
      setRoles(Object.keys(r.roles));
    } catch (e) {
      setMsg((e as Error).message);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load
    load();
  }, [load]);

  async function run(fn: () => Promise<unknown>, ok: string) {
    setMsg(null);
    try {
      await fn();
      setMsg(ok);
      await load();
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  const input = "rounded-md border border-line bg-surface px-2 py-1.5 text-sm";
  return (
    <section className="mt-4 rounded-lg border border-line bg-surface p-4">
      <h2 className="mb-3 font-semibold">Users</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-muted">
            <tr><th className="py-1 pr-4 font-medium">Email</th><th className="pr-4 font-medium">Role</th><th className="pr-4 font-medium">Execute</th><th className="pr-4 font-medium">Active</th><th className="font-medium">Last sign-in</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {users.map((u) => (
              <tr key={u.id}>
                <td className="py-1.5 pr-4">{u.email}</td>
                <td className="pr-4">
                  <select className={input} value={u.role} onChange={(e) => run(() => authApi.updateUser(u.id, { role: e.target.value }), "Role updated")}>
                    {roles.map((r) => <option key={r}>{r}</option>)}
                  </select>
                </td>
                <td className="pr-4 text-muted">{u.execute_enabled ? "yes" : "no"}</td>
                <td className="pr-4">
                  <button disabled={u.id === selfId} className="text-accent disabled:text-muted"
                    onClick={() => run(() => authApi.updateUser(u.id, { is_active: !u.is_active }), u.is_active ? "User deactivated" : "User activated")}>
                    {u.is_active ? "active" : "inactive"}
                  </button>
                </td>
                <td className="text-muted">{u.last_login_at ? new Date(u.last_login_at).toLocaleString("en-AU") : "never"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <form
        className="mt-4 flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          run(() => authApi.createUser(form), "User created").then(() => setForm({ email: "", name: "", role: "viewer", password: "" }));
        }}
      >
        <input className={input} type="email" placeholder="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input className={input} placeholder="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <select className={input} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
          {roles.map((r) => <option key={r}>{r}</option>)}
        </select>
        <input className={input} type="password" placeholder="password (12+ chars)" autoComplete="new-password" required minLength={12}
          value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <button className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white">Add user</button>
      </form>
      {msg && <p className="mt-2 text-sm text-muted" role="status">{msg}</p>}
      <p className="mt-3 text-xs text-muted">Google Ads execute permission can only be granted from the server CLI, not here.</p>
    </section>
  );
}
