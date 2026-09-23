"""P02 — operator CLI. Run from backend/:

    python -m app.modules.p02_auth.cli create-admin          # first admin (prompts for email + password)
    python -m app.modules.p02_auth.cli reset-password EMAIL
    python -m app.modules.p02_auth.cli set-execute EMAIL on|off

`set-execute` is the ONLY way to grant the execute permission. Live Google Ads changes additionally
require P16 approval records, the P17 flag and ADS_EXECUTION_KILL_SWITCH=false.
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.modules.p02_auth.models import User
from app.modules.p02_auth.security import hash_password
from app.modules.p02_auth.service import create_user, normalise_email, validate_password
from app.shared.db import session_scope
from app.shared.errors import AppError


def _prompt_password() -> str:
    pw = getpass.getpass("Password (min 12 chars): ")
    if pw != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match")
    validate_password(pw)
    return pw


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="p02_auth.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create-admin")
    rp = sub.add_parser("reset-password")
    rp.add_argument("email")
    se = sub.add_parser("set-execute")
    se.add_argument("email")
    se.add_argument("state", choices=["on", "off"])
    args = p.parse_args(argv)

    try:
        with session_scope() as db:
            if args.cmd == "create-admin":
                email = input("Admin email: ").strip()
                name = input("Name: ").strip()
                user = create_user(db, email=email, name=name, role="admin", password=_prompt_password())
                print(f"Created admin {user.email} (id {user.id})")
                return

            user = db.scalar(select(User).where(User.email == normalise_email(args.email)))
            if user is None:
                sys.exit(f"No user {args.email}")
            if args.cmd == "reset-password":
                user.password_hash = hash_password(_prompt_password())
                print(f"Password reset for {user.email}")
            elif args.cmd == "set-execute":
                enable = args.state == "on"
                if enable and input(f"Type EXECUTE to let {user.email} push changes to Google Ads: ") != "EXECUTE":
                    sys.exit("Cancelled")
                user.execute_enabled = enable
                print(f"execute_enabled={enable} for {user.email}")
    except AppError as e:
        sys.exit(f"Error: {e.message}")


if __name__ == "__main__":
    main()
