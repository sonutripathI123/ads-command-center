"""P05 — sync from the command line (e.g. Windows Task Scheduler until the P05 scheduler exists). Run from backend/:

    python -m app.modules.p05_ads_sync.cli sync            # all active accounts, incremental
    python -m app.modules.p05_ads_sync.cli sync --days 90  # full re-sync of last 90 days
"""
import argparse
import json

from app.modules.p04_ads_connection.interface import active_accounts
from app.modules.p05_ads_sync import sync
from app.modules.p05_ads_sync.models import SyncRun
from app.shared.db import session_scope


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="p05_ads_sync.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync")
    s.add_argument("--days", type=int, default=None)
    args = p.parse_args(argv)

    with session_scope() as db:
        accounts = active_accounts(db)
        run_ids = [(a, sync.start_run(db, a, days=args.days, user_id=None).id) for a in accounts]
    if not run_ids:
        print("No active ads accounts (add one on the Ads Accounts page).")
    for acc, run_id in run_ids:
        print(f"Syncing {acc.customer_id} {acc.descriptive_name or ''} ...", flush=True)
        sync.execute_run(run_id)
        with session_scope() as db:
            r = db.get(SyncRun, run_id)
            print(f"  {r.status} {r.date_from}..{r.date_to} rows={json.loads(r.counts)}")
            for step, err in json.loads(r.errors).items():
                print(f"  ! {step}: {err}")


if __name__ == "__main__":
    main()
