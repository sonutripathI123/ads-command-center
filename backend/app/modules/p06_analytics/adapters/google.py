"""P06 — READ-ONLY Google adapters: service-account auth (JWT, signed with `cryptography`), GA4 Data API
runReport, Search Console searchAnalytics.query. No write calls exist here."""
import base64
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

SCOPES = ("https://www.googleapis.com/auth/analytics.readonly", "https://www.googleapis.com/auth/webmasters.readonly")
GA4 = "https://analyticsdata.googleapis.com/v1beta"
GSC = "https://www.googleapis.com/webmasters/v3"


class GoogleDataError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.message, self.status = message, status


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _raise(r: httpx.Response, what: str) -> None:
    if r.is_success:
        return
    try:
        err = r.json().get("error")
        msg = err.get("message") if isinstance(err, dict) else (r.json().get("error_description") or err)
    except ValueError:
        msg = r.text[:200]
    raise GoogleDataError(f"{what}: {msg}", r.status_code)


@dataclass
class ServiceAccount:
    path: str
    http: httpx.Client
    _token: str | None = None
    _exp: float = 0
    info: dict = field(default_factory=dict)

    def __post_init__(self):
        p = Path(self.path)
        if not p.is_file():
            raise GoogleDataError(f"Service account file not found: {self.path}")
        self.info = json.loads(p.read_text(encoding="utf-8"))

    @property
    def email(self) -> str:
        return self.info.get("client_email", "")

    def token(self) -> str:
        if self._token and time.time() < self._exp - 60:
            return self._token
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT", "kid": self.info.get("private_key_id", "")}
        claims = {"iss": self.email, "scope": " ".join(SCOPES), "aud": self.info["token_uri"], "iat": now, "exp": now + 3600}
        signing_input = f"{_b64(json.dumps(header).encode())}.{_b64(json.dumps(claims).encode())}".encode()
        key = serialization.load_pem_private_key(self.info["private_key"].encode(), password=None)
        sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        r = self.http.post(self.info["token_uri"], data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                                          "assertion": f"{signing_input.decode()}.{_b64(sig)}"})
        _raise(r, "Service account sign-in failed")
        b = r.json()
        self._token, self._exp = b["access_token"], now + int(b.get("expires_in", 3600))
        return self._token

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token()}"}


class GA4Client:
    def __init__(self, sa: ServiceAccount):
        self.sa = sa

    def report(self, property_id: str, *, start: str, end: str, dimensions: list[str], metrics: list[str],
               limit: int = 100_000) -> list[dict]:
        """→ rows as {dimension/metric name: value}. Follows offset pagination."""
        rows, offset = [], 0
        while True:
            r = self.sa.http.post(f"{GA4}/properties/{property_id}:runReport", headers=self.sa.headers(), json={
                "dateRanges": [{"startDate": start, "endDate": end}], "dimensions": [{"name": d} for d in dimensions],
                "metrics": [{"name": m} for m in metrics], "limit": min(limit, 100_000), "offset": offset})
            _raise(r, f"GA4 property {property_id}")
            b = r.json()
            for row in b.get("rows", []):
                rec = {d: v["value"] for d, v in zip(dimensions, row.get("dimensionValues", []))}
                rec.update({m: v["value"] for m, v in zip(metrics, row.get("metricValues", []))})
                rows.append(rec)
            offset += len(b.get("rows", []))
            if not b.get("rows") or offset >= int(b.get("rowCount", 0)) or offset >= limit:
                return rows


class SearchConsoleClient:
    def __init__(self, sa: ServiceAccount):
        self.sa = sa

    def query(self, site_url: str, *, start: str, end: str, dimensions: list[str], row_limit: int = 25_000,
              max_rows: int = 100_000) -> list[dict]:
        rows, start_row = [], 0
        while True:
            r = self.sa.http.post(f"{GSC}/sites/{quote(site_url, safe='')}/searchAnalytics/query", headers=self.sa.headers(),
                                  json={"startDate": start, "endDate": end, "dimensions": dimensions,
                                        "rowLimit": row_limit, "startRow": start_row})
            _raise(r, f"Search Console {site_url}")
            batch = r.json().get("rows", [])
            for x in batch:
                rows.append({**dict(zip(dimensions, x["keys"])), "clicks": x.get("clicks", 0),
                             "impressions": x.get("impressions", 0), "position": x.get("position", 0)})
            start_row += len(batch)
            if len(batch) < row_limit or start_row >= max_rows:
                return rows
