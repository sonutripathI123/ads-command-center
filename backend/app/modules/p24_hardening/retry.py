"""P24 — retry helper for flaky external calls (Google/Anthropic APIs): a transient network blip or a
momentary 5xx/429 shouldn't fail the whole request. Retries ONLY the exception types the caller names;
anything else (bad input, auth failure, policy refusal) is raised immediately, unchanged."""
import time
from collections.abc import Callable
from typing import TypeVar

import httpx

from app.shared.logging import get_logger

T = TypeVar("T")
log = get_logger("P24")


def with_retry(fn: Callable[[], T], *, retry_on: tuple[type[Exception], ...], attempts: int = 3,
               base_delay: float = 1.0, sleep: Callable[[float], None] = time.sleep) -> T:
    """Call fn(); on an exception matching retry_on, wait base_delay * 2**i seconds and try again, up to
    `attempts` total tries. The last exception is re-raised unchanged if every attempt fails."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as e:
            last = e
            if i == attempts - 1:
                raise
            log.warning("retrying_after_error", extra={"attempt": i + 1, "attempts": attempts, "error": str(e)[:200]})
            sleep(base_delay * (2 ** i))
    raise last  # pragma: no cover — unreachable, satisfies type checkers


RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_WAIT = 10.0


def _retry_after(r: httpx.Response) -> float | None:
    try:
        return float(r.headers.get("retry-after", ""))
    except ValueError:
        return None


def request_with_retry(do: Callable[[], httpx.Response], *, attempts: int = 3, base_delay: float = 1.0) -> httpx.Response:
    """For idempotent READ requests to Google (searches, reports, token refresh). Retries timeouts / connection errors and
    HTTP 429 / 5xx with backoff (honouring Retry-After, capped). Returns the LAST response even if it is still an error, so the
    caller's normal error handling is unchanged; raises the last transport error only if every attempt failed to connect.
    Never use it for anything that changes data (P17 mutations are deliberately not retried)."""
    for i in range(attempts):
        last = i == attempts - 1
        try:
            r = do()
        except httpx.TransportError as e:
            if last:
                raise
            log.warning("retrying_after_transport_error", extra={"attempt": i + 1, "error": type(e).__name__})
            time.sleep(min(base_delay * 2 ** i, MAX_WAIT))
            continue
        if r.status_code in RETRY_STATUS and not last:
            log.warning("retrying_after_http_status", extra={"attempt": i + 1, "status": r.status_code})
            time.sleep(min(_retry_after(r) or base_delay * 2 ** i, MAX_WAIT))
            continue
        return r
    raise RuntimeError("unreachable")  # pragma: no cover

