"""SHARED (owner: P00) — operator CLI for feature flags. Server-side only; there is no HTTP endpoint for this.

    python -m app.shared.flags_cli list
    python -m app.shared.flags_cli set crawler.enabled on --reason "scan our own websites" --by "you@example.com"
    python -m app.shared.flags_cli clear crawler.enabled          # back to the declared default

Kill-switch-guarded flags (Google Ads execution, P17) cannot be changed here: they stay off until P16/P17/P22
provide their own approved path, and ADS_EXECUTION_KILL_SWITCH overrides them regardless.
"""
import argparse
import getpass
import sys
from datetime import UTC, datetime

from app.shared.db import session_scope
from app.shared.feature_flags import FeatureFlagOverride, resolve_all
from app.shared.registry import load_registry


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="flags_cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("set")
    s.add_argument("key")
    s.add_argument("state", choices=["on", "off"])
    s.add_argument("--reason", required=True, help="why (stored with the change)")
    s.add_argument("--by", default=None, help="who (defaults to the OS user)")
    c = sub.add_parser("clear")
    c.add_argument("key")
    args = p.parse_args(argv)

    with session_scope() as db:
        if args.cmd == "list":
            for f in resolve_all(db):
                print(f"{f.key:40} {'ON ' if f.enabled else 'off'}  ({f.source})  {f.module_id}  {f.description}")
            return 0
        spec = load_registry().flags.get(args.key)
        if spec is None:
            print(f"Unknown flag '{args.key}'. Run 'list' to see declared flags.", file=sys.stderr)
            return 2
        if spec.kill_switch_guarded:
            print(f"'{args.key}' controls live Google Ads execution and cannot be changed with this tool.", file=sys.stderr)
            return 3
        row = db.get(FeatureFlagOverride, args.key)
        if args.cmd == "clear":
            if row is not None:
                db.delete(row)
            print(f"{args.key}: override removed (default {'on' if spec.default else 'off'})")
            return 0
        if not args.reason.strip():
            print("--reason must not be empty", file=sys.stderr)
            return 2
        row = row or FeatureFlagOverride(key=args.key, enabled=False)
        row.enabled, row.reason = args.state == "on", args.reason.strip()[:1000]
        row.updated_by, row.updated_at = (args.by or getpass.getuser())[:255], datetime.now(UTC)
        db.add(row)
        print(f"{args.key}: {args.state} (reason: {row.reason}; by {row.updated_by})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
