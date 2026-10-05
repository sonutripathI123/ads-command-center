"""P17 — operator CLI: the ONLY way to switch live execution on or off. Run on the server, from backend/:

    python -m app.modules.p17_ads_execution.cli status
    python -m app.modules.p17_ads_execution.cli enable --reason "why" [--by you@example.com]   # asks you to type a phrase
    python -m app.modules.p17_ads_execution.cli disable --reason "why"

`enable` only sets the P17 flag. Live execution ALSO needs ADS_EXECUTION_KILL_SWITCH=false in the environment —
that stays a deliberate, separate step. Nothing here talks to Google Ads.
"""
import argparse
import getpass
import sys
from datetime import UTC, datetime

from app.modules.p17_ads_execution import google
from app.modules.p17_ads_execution.service import status
from app.modules.p22_security_audit.interface import record as audit_record
from app.shared.db import session_scope
from app.shared.feature_flags import FeatureFlagOverride

PHRASE = "ENABLE LIVE EXECUTION"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="p17_ads_execution.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    for name in ("enable", "disable"):
        s = sub.add_parser(name)
        s.add_argument("--reason", required=True)
        s.add_argument("--by", default=None)
    args = p.parse_args(argv)

    with session_scope() as db:
        if args.cmd == "status":
            for k, v in status(db).items():
                print(f"{k}: {v}")
            return 0
        if not args.reason.strip():
            print("--reason must not be empty", file=sys.stderr)
            return 2
        want, who = args.cmd == "enable", getpass.getuser()[:255]   # --by is ignored: the audit actor can't be spoofed
        if want and not sys.stdin.isatty():
            print("Run this from an interactive terminal (the confirmation can't be piped).", file=sys.stderr)
            return 3
        if want and input(f'Type "{PHRASE}" to switch the live-execution flag ON: ').strip() != PHRASE:
            print("Not confirmed — nothing changed.", file=sys.stderr)
            return 3
        row = db.get(FeatureFlagOverride, google.FLAG) or FeatureFlagOverride(key=google.FLAG, enabled=False)
        row.enabled, row.reason, row.updated_by, row.updated_at = want, args.reason.strip()[:1000], who, datetime.now(UTC)
        db.add(row)
        audit_record(db, module_id="P17", action="execution_flag_" + ("on" if want else "off"), actor=who,
                     entity_type="flag", entity_id=google.FLAG, before=None, after={"enabled": want}, note=args.reason, commit=False)
        print(f"{google.FLAG}: {'ON' if want else 'off'} (by {who})")
        for k, v in status(db).items():
            print(f"  {k}: {v}")
        if want:
            print("Note: live execution still stays blocked while ADS_EXECUTION_KILL_SWITCH=true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
