"""P23 — route auditor. Walks every /api/v1 route of a FastAPI app and checks the access rules the whole product
depends on. In-process only (starlette TestClient), no network. Findings are plain data, so tests and the CLI share them."""
import re
from dataclasses import dataclass

# Routes that are meant to answer without a session. Anything else must say 401 when called anonymously.
PUBLIC_ROUTES: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/api/v1/foundation/health"), ("GET", "/api/v1/foundation/modules"), ("GET", "/api/v1/foundation/flags"),
    ("POST", "/api/v1/auth/login"), ("POST", "/api/v1/auth/logout"),
})
# Writes a READ-only user may do on purpose: sign in/out, and generate a report (P19: "it only reads data").
READ_ONLY_WRITES_ALLOWED: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/api/v1/auth/logout"), ("POST", "/api/v1/auth/login"), ("POST", "/api/v1/reports/runs"),
})
_PARAM = re.compile(r"\{[^}]+\}")


@dataclass(frozen=True)
class Finding:
    method: str
    path: str
    expected: str
    got: int

    def __str__(self) -> str:
        return f"{self.method} {self.path}: expected {self.expected}, got HTTP {self.got}"


def list_routes(app) -> list[tuple[str, str]]:
    """(METHOD, path template) for every /api/v1 operation, sorted."""
    out = [(m.upper(), p) for p, ms in app.openapi()["paths"].items() if p.startswith("/api/v1")
           for m in ms if m.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}]
    return sorted(out)


def _send(client, method: str, path: str):
    url = _PARAM.sub("1", path)
    return client.request(method, url, json={} if method != "GET" else None)


def audit_anonymous(client, app) -> list[Finding]:
    """Without a session cookie every non-public route must answer 401."""
    return [Finding(m, p, "401", r.status_code) for m, p in list_routes(app)
            if (m, p) not in PUBLIC_ROUTES and (r := _send(client, m, p)).status_code != 401]


def audit_read_only_writes(client, app) -> list[Finding]:
    """A user holding only the READ permission must be refused (403) on every write route. The caller overrides the
    current-user dependency with such a user; the permission check runs before the handler, so nothing is executed."""
    return [Finding(m, p, "403", r.status_code) for m, p in list_routes(app)
            if m != "GET" and (m, p) not in READ_ONLY_WRITES_ALLOWED and (r := _send(client, m, p)).status_code != 403]
