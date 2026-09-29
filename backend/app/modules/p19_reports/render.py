"""P19 — exports. CSV: one block per section. HTML: self-contained, print-ready page — the browser's
"Print → Save as PDF" produces the PDF (no extra PDF library)."""
import csv
import html
import io


def _fmt(v, key: str = "") -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if key in ("ctr", "conv_rate", "rate", "change"):
            return f"{v:.1%}" if key != "change" else f"{v:+.0%}"
        return f"{v:,.2f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def tables(r: dict) -> list[tuple[str, list[str], list[list]]]:
    """(title, header, rows) for every tabular section present in the report."""
    c = r["content"]
    out = []
    if c.get("kpis"):
        out.append(("Key figures", ["Metric", "This period", "Previous", "Change"],
                    [[k["label"], _fmt(k["value"], k["key"]), _fmt(k["previous"], k["key"]), _fmt(k["change"], "change")] for k in c["kpis"]]))
    if c.get("campaigns"):
        out.append(("Campaigns", ["Campaign", "Status", "Clicks", "Cost", "Conv.", "Cost/conv."],
                    [[x["name"], x["status"], _fmt(x["clicks"]), _fmt(x["cost"]), _fmt(x["conversions"]), _fmt(x["cost_per_conversion"])]
                     for x in c["campaigns"]]))
    if c.get("search_terms"):
        out.append(("Top search terms by cost", ["Search term", "Clicks", "Cost", "Conv."],
                    [[x["search_term"], _fmt(x["clicks"]), _fmt(x["cost"]), _fmt(x["conversions"])] for x in c["search_terms"]]))
    for f in c.get("funnels", []):
        out.append((f"Funnel — {f['website']}", ["Stage", "Value", "Rate", "Cost per", "Source"],
                    [[s["label"], _fmt(s["value"]) if s["value"] is not None else "not measured", _fmt(s["rate"], "rate"),
                      _fmt(s["cost_per"]), s["source"] + (" (estimate)" if s["estimated"] else "")] for s in f["stages"]]))
    if c.get("ga4_channels"):
        out.append(("GA4 traffic by channel", ["Channel", "Sessions", "Engaged", "Key events"],
                    [[x["channel"], _fmt(x["sessions"]), _fmt(x["engaged_sessions"]), _fmt(x["key_events"])] for x in c["ga4_channels"]]))
    if c.get("gsc_queries"):
        out.append(("Search Console — top queries", ["Query", "Clicks", "Impressions", "Avg. position"],
                    [[x["query"], _fmt(x["clicks"]), _fmt(x["impressions"]), _fmt(x["position"])] for x in c["gsc_queries"]]))
    if c.get("bookings"):
        b = c["bookings"]
        out.append(("Bookings", ["Channel", "Bookings", "Revenue (AUD)"],
                    [[x["channel"], _fmt(x["count"]), _fmt(x["revenue"])] for x in b["by_channel"]] + [["Total", _fmt(b["count"]), _fmt(b["revenue"])]]))
    if c.get("recommendations"):
        out.append(("Open recommendations", ["Priority", "Severity", "Recommendation", "Status"],
                    [[x["priority"], x["severity"], x["title"], x["status"]] for x in c["recommendations"]]))
    if c.get("approvals"):
        out.append(("Approval decisions", ["Change", "Decision", "By", "When"],
                    [[x["title"], x["status"], x["decided_by"] or "", str(x["decided_at"])[:16]] for x in c["approvals"]]))
    if c.get("alerts"):
        out.append(("Open alerts", ["Severity", "Alert", "What to do"], [[x["severity"], x["title"], x["action"]] for x in c["alerts"]]))
    if c.get("issues"):
        out.append(("Tracking & data issues", ["Severity", "Issue", "Detail"], [[x["severity"], x["title"], x["detail"]] for x in c["issues"]]))
    return out


def to_csv(r: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([r["title"]])
    w.writerow([f"Period: {r['period_label']} ({r['date_from']} to {r['date_to']})", f"Generated {str(r['created_at'])[:16]} by {r['created_by']}"])
    for line in r["content"].get("headline", []):
        w.writerow([line])
    for title, header, rows in tables(r):
        w.writerow([])
        w.writerow([title])
        w.writerow(header)
        w.writerows(rows)
    return buf.getvalue()


CSS = """body{font:13px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;color:#111;margin:24px;max-width:1000px}
h1{font-size:20px;margin:0}h2{font-size:14px;margin:22px 0 6px;border-bottom:1px solid #ccc;padding-bottom:3px}
.meta{color:#555;margin:4px 0 12px}table{border-collapse:collapse;width:100%;margin-bottom:6px}
th,td{text-align:left;padding:3px 8px 3px 0;border-bottom:1px solid #eee;vertical-align:top}th{color:#555;font-weight:600}
td.n{text-align:right;font-variant-numeric:tabular-nums}ul{margin:4px 0 0 18px;padding:0}
.bar{position:sticky;top:0;background:#fff;padding:8px 0;margin-bottom:8px}
@media print{.bar{display:none}body{margin:0}h2{break-after:avoid}tr{break-inside:avoid}}"""


def to_html(r: dict) -> str:
    e = html.escape
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{e(r['title'])}</title><style>{CSS}</style></head><body>",
             "<div class='bar'><button onclick='window.print()'>Print / Save as PDF</button></div>",
             f"<h1>{e(r['title'])}</h1><p class='meta'>{e(r['period_label'])} ({r['date_from']} to {r['date_to']}) · generated "
             f"{e(str(r['created_at'])[:16])} UTC by {e(r['created_by'] or '')}</p>"]
    if r["content"].get("headline"):
        parts.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in r["content"]["headline"]) + "</ul>")
    for title, header, rows in tables(r):
        parts.append(f"<h2>{e(title)}</h2><table><thead><tr>" + "".join(f"<th>{e(h)}</th>" for h in header) + "</tr></thead><tbody>")
        for row in rows:
            parts.append("<tr>" + "".join(f"<td{' class=n' if i and _num(v) else ''}>{e(str(v))}</td>" for i, v in enumerate(row)) + "</tr>")
        parts.append("</tbody></table>")
    for note in r["content"].get("notes", []):
        parts.append(f"<p class='meta'>{e(note)}</p>")
    parts.append("</body></html>")
    return "".join(parts)


def _num(v) -> bool:
    s = str(v).replace(",", "").replace("%", "").replace("+", "").replace("-", "", 1)
    return s.replace(".", "", 1).isdigit()
