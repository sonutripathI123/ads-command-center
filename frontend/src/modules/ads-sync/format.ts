// P05 — number formatting (en-AU).
export const money = (v: number | null | undefined, currency = "AUD") =>
  v === null || v === undefined ? "—" : new Intl.NumberFormat("en-AU", { style: "currency", currency, maximumFractionDigits: 2 }).format(v);
export const num = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined ? "—" : new Intl.NumberFormat("en-AU", { maximumFractionDigits: digits }).format(v);
export const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`);
export const title = (s: string | null | undefined) =>
  s ? s.toLowerCase().replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "—";
export const ago = (iso: string | null) => {
  if (!iso) return "never";
  const mins = Math.round((Date.now() - new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z").getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 1440) return `${Math.round(mins / 60)} h ago`;
  return `${Math.round(mins / 1440)} d ago`;
};
