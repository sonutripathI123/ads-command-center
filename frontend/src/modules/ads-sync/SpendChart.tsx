"use client";
// P05 — daily spend: single-series bar chart (accent), thin bars with rounded tops, hover tooltip,
// recessive axis. The table below the chart is the accessible data view.
import { useState } from "react";
import { money, num } from "./format";

type Day = { date: string; cost: number; clicks: number; conversions: number };

export function SpendChart({ daily, currency }: { daily: Day[]; currency: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 720, H = 180, PAD_L = 44, PAD_B = 22, PAD_T = 8;
  const max = Math.max(1, ...daily.map((d) => d.cost));
  const step = Math.pow(10, Math.floor(Math.log10(max)));
  const top = Math.ceil(max / step) * step;
  const plotW = W - PAD_L, plotH = H - PAD_B - PAD_T;
  const slot = plotW / Math.max(daily.length, 1);
  const barW = Math.max(2, Math.min(18, slot - 2));
  const y = (v: number) => PAD_T + plotH - (v / top) * plotH;
  const ticks = [0, top / 2, top];
  const labelEvery = Math.ceil(daily.length / 8);
  const h = hover !== null ? daily[hover] : null;

  return (
    <figure className="relative">
      <figcaption className="mb-2 text-sm font-medium">Daily spend</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img"
        aria-label={`Daily spend, ${daily.length} days, peak ${money(max, currency)}`} onMouseLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD_L} x2={W} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth={1} />
            <text x={PAD_L - 6} y={y(t) + 4} textAnchor="end" fontSize="10" fill="var(--muted)">{money(t, currency).replace(/\.00$/, "")}</text>
          </g>
        ))}
        {daily.map((d, i) => {
          const x = PAD_L + i * slot + (slot - barW) / 2;
          const bh = Math.max(0, PAD_T + plotH - y(d.cost));
          const r = Math.min(4, barW / 2, bh);
          return (
            <g key={d.date} onMouseEnter={() => setHover(i)}>
              <rect x={PAD_L + i * slot} y={PAD_T} width={slot} height={plotH} fill="transparent" />
              {bh > 0 && (
                <path fill="var(--accent)" opacity={hover === null || hover === i ? 1 : 0.45}
                  d={`M${x},${y(0)} V${y(d.cost) + r} Q${x},${y(d.cost)} ${x + r},${y(d.cost)} H${x + barW - r} Q${x + barW},${y(d.cost)} ${x + barW},${y(d.cost) + r} V${y(0)} Z`} />
              )}
              {i % labelEvery === 0 && (
                <text x={x + barW / 2} y={H - 6} textAnchor="middle" fontSize="10" fill="var(--muted)">
                  {new Date(d.date + "T00:00:00").toLocaleDateString("en-AU", { day: "numeric", month: "short" })}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {h && hover !== null && (
        <div className="pointer-events-none absolute top-6 rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs shadow-sm"
          style={{ left: `min(calc(${((PAD_L + hover * slot) / W) * 100}% + 8px), calc(100% - 160px))` }}>
          <div className="font-medium">{new Date(h.date + "T00:00:00").toLocaleDateString("en-AU", { weekday: "short", day: "numeric", month: "short" })}</div>
          <div>Spend {money(h.cost, currency)}</div>
          <div className="text-muted">{num(h.clicks)} clicks · {num(h.conversions, 1)} conv.</div>
        </div>
      )}
    </figure>
  );
}
