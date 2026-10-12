"""P23 — QA command line.   python -m app.modules.p23_testing_qa.cli [--roles]
Default: anonymous route audit (safe: every request is refused before any handler runs).
--roles also runs the READ-only write audit. Use it on a development database only."""
import argparse
import sys

from fastapi.testclient import TestClient

from app.modules.p23_testing_qa import audit


def run(roles: bool = False) -> int:
    from app.main import create_app

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    findings = audit.audit_anonymous(client, app)
    print(f"routes audited: {len(audit.list_routes(app))}; anonymous access findings: {len(findings)}")
    if roles:
        from app.modules.p02_auth.interface import CurrentUser, Permission, get_current_user

        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            id=0, email="qa@example.com", name="qa", role="viewer", permissions=frozenset({Permission.READ}))
        rf = audit.audit_read_only_writes(client, app)
        print(f"read-only user write findings: {len(rf)}")
        findings += rf
    for f in findings:
        print("  FAIL", f)
    return 1 if findings else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--roles", action="store_true", help="also check that a READ-only user cannot write (dev DB only)")
    sys.exit(run(ap.parse_args().roles))
