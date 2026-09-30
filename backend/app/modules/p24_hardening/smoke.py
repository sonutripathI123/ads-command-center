"""P24 — post-deploy smoke test: hits a running instance over plain HTTP(S), no DB/app import needed.
Run against ANY environment (local, staging, prod) right after a deploy.

    python -m app.modules.p24_hardening.smoke --base-url https://api.yourdomain.com.au
    python -m app.modules.p24_hardening.smoke --base-url https://api.yourdomain.com.au --email you@x.com --password ...
"""
import argparse
import sys

import httpx


def _check(client: httpx.Client, method: str, path: str, expect: set[int], **kw) -> tuple[bool, str]:
    try:
        r = client.request(method, path, **kw)
    except httpx.RequestError as e:
        return False, f"{method} {path}: could not connect ({e})"
    ok = r.status_code in expect
    return ok, f"{method} {path}: {r.status_code}" + ("" if ok else f" (expected one of {sorted(expect)})")


def run(base_url: str, email: str | None, password: str | None) -> int:
    results: list[tuple[bool, str]] = []
    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        results.append(_check(client, "GET", "/api/v1/foundation/health", {200}))
        results.append(_check(client, "GET", "/api/v1/foundation/modules", {200}))
        results.append(_check(client, "GET", "/api/v1/foundation/flags", {200}))
        # Every mounted module's real base route should exist (401 = auth required, not 404/500).
        for path in ("/api/v1/auth/me", "/api/v1/websites", "/api/v1/ads-connection/status",
                     "/api/v1/ads-sync/accounts", "/api/v1/conversions/websites", "/api/v1/audit/accounts",
                     "/api/v1/keywords/accounts/1/negatives", "/api/v1/creatives/accounts",
                     "/api/v1/landing-pages/accounts", "/api/v1/competitors/accounts", "/api/v1/funnel/websites",
                     "/api/v1/recommendations/accounts", "/api/v1/campaign-builder/accounts",
                     "/api/v1/approvals/accounts", "/api/v1/monitoring/accounts", "/api/v1/reports/options",
                     "/api/v1/experiments/accounts", "/api/v1/business-rules",
                     "/api/v1/security/audit-logs"):
            results.append(_check(client, "GET", path, {200, 401, 422}))
        if email and password:
            r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
            results.append((r.status_code == 200, f"POST /api/v1/auth/login: {r.status_code}"))
            if r.status_code == 200:
                me = client.get("/api/v1/auth/me")
                results.append((me.status_code == 200, f"GET /api/v1/auth/me (signed in): {me.status_code}"))

    for ok, msg in results:
        print(("PASS" if ok else "FAIL") + " — " + msg)
    failed = sum(1 for ok, _ in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True, help="e.g. https://api.yourdomain.com.au")
    p.add_argument("--email", default=None)
    p.add_argument("--password", default=None)
    args = p.parse_args()
    sys.exit(run(args.base_url, args.email, args.password))
