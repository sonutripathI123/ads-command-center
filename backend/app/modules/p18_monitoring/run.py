"""P18 — scheduled run for Windows Task Scheduler / cron:

    cd backend && .venv\\Scripts\\python.exe -m app.modules.p18_monitoring.run

Does nothing unless flag `monitoring.scheduled.enabled` is on. Sync Google Ads (P05) before it for fresh numbers."""
from app.modules.p18_monitoring import service
from app.shared.db import session_scope


def main() -> int:
    with session_scope() as db:
        results = service.run_scheduled(db)
        for r in results:
            print(f"account {r.account_id}: {r.status}, {r.signals} signals, {r.opened} new, {r.resolved} resolved")
        if not results:
            print("nothing run (flag monitoring.scheduled.enabled is off, or no active accounts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
