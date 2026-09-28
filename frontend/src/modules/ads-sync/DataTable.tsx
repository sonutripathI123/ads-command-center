"use client";
// P05 — sortable table used by all data pages.
import { useMemo, useState, type ReactNode } from "react";

export type Column<T> = {
  key: string;
  label: string;
  value: (row: T) => number | string | null;
  render?: (row: T) => ReactNode;
  numeric?: boolean;
};

export function DataTable<T>({ rows, columns, rowKey, initialSort, empty = "No data for this period." }: {
  rows: T[]; columns: Column<T>[]; rowKey: (r: T) => string; initialSort?: string; empty?: string;
}) {
  const [sort, setSort] = useState<{ key: string; desc: boolean }>({ key: initialSort ?? columns[0].key, desc: true });
  const sorted = useMemo(() => {
    const col = columns.find((c) => c.key === sort.key) ?? columns[0];
    return [...rows].sort((a, b) => {
      const va = col.value(a), vb = col.value(b);
      if (va === vb) return 0;
      if (va === null) return 1;
      if (vb === null) return -1;
      const cmp = va < vb ? -1 : 1;
      return sort.desc ? -cmp : cmp;
    });
  }, [rows, columns, sort]);

  if (!rows.length) return <p className="py-6 text-center text-sm text-muted">{empty}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-muted">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={`whitespace-nowrap py-1.5 pr-4 font-medium ${c.numeric ? "text-right" : ""}`}
                aria-sort={sort.key === c.key ? (sort.desc ? "descending" : "ascending") : undefined}>
                <button className="hover:text-fg" onClick={() => setSort((s) => ({ key: c.key, desc: s.key === c.key ? !s.desc : true }))}>
                  {c.label}{sort.key === c.key ? (sort.desc ? " ↓" : " ↑") : ""}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {sorted.map((r) => (
            <tr key={rowKey(r)} className="hover:bg-surface-2">
              {columns.map((c) => (
                <td key={c.key} className={`py-1.5 pr-4 ${c.numeric ? "text-right tabular-nums" : ""}`}>
                  {c.render ? c.render(r) : String(c.value(r) ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-muted">{rows.length} rows · click a column to sort</p>
    </div>
  );
}
