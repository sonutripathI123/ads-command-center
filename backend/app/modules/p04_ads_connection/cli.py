"""P04 — operator CLI. Run from backend/:

    python -m app.modules.p04_ads_connection.cli check-env CCM
    python -m app.modules.p04_ads_connection.cli import-env CCM

Reads <PREFIX>_GOOGLE_ADS_REFRESH_TOKEN and <PREFIX>_GOOGLE_ADS_CUSTOMER_ID (optional
<PREFIX>_GOOGLE_ADS_LOGIN_CUSTOMER_ID) from backend/.env, plus the shared GOOGLE_OAUTH_CLIENT_ID /
GOOGLE_OAUTH_CLIENT_SECRET / GOOGLE_ADS_DEVELOPER_TOKEN. `import-env` stores the refresh token encrypted
as a connection and adds the account. Secret values are never printed. Read-only toward Google Ads.
"""
import argparse
import sys

import httpx
from dotenv import dotenv_values

from app.modules.p04_ads_connection import service
from app.modules.p04_ads_connection.adapters.google_ads import GoogleApiError
from app.modules.p04_ads_connection.crypto import encrypt
from app.modules.p04_ads_connection.models import Connection
from app.shared.db import session_scope
from app.shared.errors import AppError


def _env(prefix: str) -> tuple[str, str, str | None]:
    env = dotenv_values(".env")
    token = (env.get(f"{prefix}_GOOGLE_ADS_REFRESH_TOKEN") or "").strip()
    cid = service.digits(env.get(f"{prefix}_GOOGLE_ADS_CUSTOMER_ID"))
    login = service.digits(env.get(f"{prefix}_GOOGLE_ADS_LOGIN_CUSTOMER_ID")) or None
    if not token:
        sys.exit(f"{prefix}_GOOGLE_ADS_REFRESH_TOKEN is empty in backend/.env")
    return token, cid, login


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="p04_ads_connection.cli")
    p.add_argument("cmd", choices=["check-env", "import-env"])
    p.add_argument("prefix", help="env prefix, e.g. CCM for Corporate Cars Melbourne")
    args = p.parse_args(argv)
    token, cid, login = _env(args.prefix.upper())

    with httpx.Client(timeout=30) as http:
        try:
            client = service.make_client(http)
            access = client.access_token(token)
            print("1/3 Google login (refresh token + OAuth client): OK")
            email = client.user_email(access)
            ids = client.list_accessible_customers(access)
            print(f"2/3 Google Ads API + developer token: OK — {len(ids)} accessible account(s): {', '.join(ids)}")
            if cid:
                info = client.customer_info(access, cid, login_customer_id=login)
                print(f"3/3 Account {cid}: '{info.descriptive_name}' {info.currency_code} {info.time_zone}"
                      f"{' (manager)' if info.is_manager else ''}")
        except (GoogleApiError, AppError) as e:
            reason = getattr(e, "reason", None) or getattr(e, "details", {})
            sys.exit(f"FAILED: {e.message} [{reason}]")

        if args.cmd == "check-env":
            return
        with session_scope() as db:
            conn = Connection(provider="google_ads", google_email=email, refresh_token_enc=encrypt(token),
                              scopes="https://www.googleapis.com/auth/adwords (imported)", status="active")
            db.add(conn)
            db.flush()
            print(f"Stored encrypted connection #{conn.id} ({email or 'unknown email'})")
            if cid:
                acc = service.add_account(db, client, connection_id=conn.id, customer_id=cid,
                                          login_customer_id=login, user_id=None)
                print(f"Added ads account {acc.customer_id} '{acc.descriptive_name}'")


if __name__ == "__main__":
    main()
