"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_GROUPS, hrefFor } from "./nav";

export function Sidebar({ statusById, onNavigate }: { statusById: Record<string, string>; onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-col gap-5 p-4 text-sm">
      <div className="px-2">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted">PPC Command Center</div>
        <div className="font-semibold">AI Google Ads Specialist</div>
      </div>
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <div className="px-2 pb-1 text-xs font-medium uppercase tracking-wider text-muted">{group.label}</div>
          <ul className="flex flex-col">
            {group.items.map((item) => {
              const href = hrefFor(item);
              const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
              const built = (statusById[item.moduleId] ?? "planned") !== "planned";
              return (
                <li key={item.slug || "overview"}>
                  <Link
                    href={href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center justify-between rounded-md px-2 py-1.5 ${
                      active ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"
                    }`}
                  >
                    <span>{item.label}</span>
                    {!built && <span className="text-[10px] text-muted">{item.moduleId}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
