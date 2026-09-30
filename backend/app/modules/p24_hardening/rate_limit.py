"""P24 — request rate limiting. Fixed-window counter per client IP; Redis-backed when REDIS_URL is reachable
(so it works across multiple backend replicas), falling back to a single-process in-memory counter otherwise
(e.g. local dev, or Redis briefly unavailable)."""
import time
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.shared.logging import get_logger, request_id_var

MODULE_ID = "P24"
log = get_logger(MODULE_ID)


class InMemoryCounter:
    def __init__(self) -> None:
        self._data: dict[str, tuple[int, int]] = {}
        self._lock = Lock()

    def incr(self, key: str, window_seconds: int) -> int:
        now = int(time.time())
        window = now - (now % window_seconds)
        with self._lock:
            start, count = self._data.get(key, (window, 0))
            if start != window:
                start, count = window, 0
            count += 1
            self._data[key] = (start, count)
            return count


class RedisCounter:
    def __init__(self, url: str) -> None:
        import redis

        self._r = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        self._r.ping()

    def incr(self, key: str, window_seconds: int) -> int:
        now = int(time.time())
        window = now - (now % window_seconds)
        rkey = f"ratelimit:{key}:{window}"
        pipe = self._r.pipeline()
        pipe.incr(rkey, 1)
        pipe.expire(rkey, window_seconds + 5)
        count, _ = pipe.execute()
        return int(count)


def build_counter(redis_url: str | None):
    """Redis when reachable (works across replicas); otherwise an in-memory fallback (logged once)."""
    if redis_url:
        try:
            return RedisCounter(redis_url)
        except Exception:
            log.warning("rate_limit_redis_unavailable", extra={"redis_url_set": True})
    return InMemoryCounter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """429 (with Retry-After) once a client IP exceeds `limit` requests per `window_seconds`."""

    def __init__(self, app, *, counter, limit: int, window_seconds: int, exempt_paths: frozenset[str] = frozenset()):
        super().__init__(app)
        self.counter = counter
        self.limit = limit
        self.window_seconds = window_seconds
        self.exempt_paths = exempt_paths

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        key = request.client.host if request.client else "unknown"
        count = self.counter.incr(key, self.window_seconds)
        if count > self.limit:
            log.warning("rate_limited", extra={"client": key, "path": request.url.path, "count": count})
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)},
                content={"error": {"code": "rate_limited", "message": "Too many requests — please slow down.",
                                   "module_id": MODULE_ID, "request_id": request_id_var.get(), "details": {}}},
            )
        return await call_next(request)
