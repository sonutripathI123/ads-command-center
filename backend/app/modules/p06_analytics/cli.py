"""P06 — GA4 + Search Console sync from the command line (Windows Task Scheduler / cron). Run from backend/:

    python -m app.modules.p06_analytics.cli sync             # every linked website, last 90 days (replaces the window, no duplicates)
    python -m app.modules.p06_analytics.cli sync --days 30

Read-only toward Google (GA4 Data API + Search Console queries). Mirrors p05_ads_sync.cli.
"""
import argparse
import json
import sys

from app.modules.p03_website_intel.interface import list_websites
from app.modules.p06_analytics import service
from app.modules.p06_analytics.models import AnalyticsSyncRun
from app.shared.db import session_scope
from app.shared.errors import AppError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="p06_analytics.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync")
    s.add_argument("--days", type=int, default=90)
    args = p.parse_args(argv)

    with session_scope() as db:
        sites = [w for w in list_websites(db) if w.ga4_property_id or w.gsc_site_url]
    if not sites:
        print("No website has a GA4 property or Search Console site linked (Websites page).")
        return 0
    failed = 0
    for w in sites:
        print(f"Syncing GA4 + Search Console for {w.domain} ...", flush=True)
        try:
            with session_scope() as db:
                run, created = service.start_sync(db, w, args.days)
                run_id = run.id
            if created:
                service.execute_sync(run_id)
        except AppError as e:
            print(f"  ! {e.message}")
            failed += 1
            continue
        with session_scope() as db:
            r = db.get(AnalyticsSyncRun, run_id)
            print(f"  {r.status} {r.date_from}..{r.date_to} rows={json.loads(r.counts)}")
            for step, err in json.loads(r.errors).items():
                print(f"  ! {step}: {err}")
            failed += r.status == "failed"
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
