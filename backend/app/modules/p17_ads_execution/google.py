"""P17 — the ONLY code in the project that talks to Google Ads' mutate endpoints (enforced by tests/isolation).

`send()` is the single choke point. Two modes:
  validate_only=True   Google checks the request and changes nothing (the body carries validateOnly=true).
  validate_only=False  a LIVE change. Re-checks the kill switch + `ads.execution.enabled` flag HERE, right before the
                       HTTP call, so no caller (or future bug) can reach Google while execution is locked.
"""
from sqlalchemy.orm import Session as DbSession

from app.modules.p04_ads_connection.interface import ApiCredentials
from app.modules.p17_ads_execution.plans import Operation
from app.shared.errors import AppError
from app.shared.feature_flags import require_enabled
from app.shared.logging import get_logger

MODULE_ID = "P17"
FLAG = "ads.execution.enabled"
log = get_logger(MODULE_ID)


class ExecutionFailed(AppError):
    status_code = 502
    code = "execution_failed"


def assert_live_allowed(db: DbSession) -> None:
    """Raises FeatureDisabled (409) unless ADS_EXECUTION_KILL_SWITCH is off AND the flag is switched on."""
    require_enabled(FLAG, db, module_id=MODULE_ID)


def _google_message(r) -> str:
    try:
        err = r.json().get("error", {})
    except ValueError:
        return r.text[:300]
    msgs = [e.get("message") for d in err.get("details", []) for e in d.get("errors", []) if e.get("message")]
    return "; ".join(msgs[:3]) or err.get("message") or r.text[:300]


def send(db: DbSession, creds: ApiCredentials, op: Operation, *, validate_only: bool) -> dict:
    if not validate_only:
        assert_live_allowed(db)
    url = f"{creds.base_url}/customers/{creds.account.customer_id}/{op.service}:mutate"
    r = creds.http.post(url, headers=creds.headers(), json=op.body(validate_only=validate_only), timeout=30.0)
    if not r.is_success:
        raise ExecutionFailed(f"Google Ads rejected the request ({r.status_code}): {_google_message(r)}", module_id=MODULE_ID,
                              details={"status": r.status_code})
    log.info("google_ads_request", extra={"service": op.service, "validate_only": validate_only, "ops": len(op.operations)})
    return r.json() if r.content else {}


def resource_names(response: dict) -> list[str]:
    return [x["resourceName"] for x in response.get("results", []) if x.get("resourceName")]
