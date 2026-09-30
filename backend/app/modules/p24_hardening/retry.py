"""P24 — retry helper for flaky external calls (Google/Anthropic APIs): a transient network blip or a
momentary 5xx/429 shouldn't fail the whole request. Retries ONLY the exception types the caller names;
anything else (bad input, auth failure, policy refusal) is raised immediately, unchanged."""
import time
from collections.abc import Callable
from typing import TypeVar

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
