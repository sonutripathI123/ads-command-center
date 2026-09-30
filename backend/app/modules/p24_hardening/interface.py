"""P24 — public interface.

    from app.modules.p24_hardening.interface import with_retry
    ...
    r = with_retry(lambda: client.beta.messages.create(...), retry_on=(anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError))

`install(app)` is called once from `app.main.create_app()` (P00) to add the rate-limit and security-header
middleware — this is the one place P24 reaches into a frozen module, and only additively (see its CHANGELOG).
"""
from fastapi import FastAPI

from app.modules.p24_hardening.config import P24Settings
from app.modules.p24_hardening.rate_limit import RateLimitMiddleware, build_counter
from app.modules.p24_hardening.retry import with_retry
from app.modules.p24_hardening.security_headers import SecurityHeadersMiddleware
from app.shared.config import get_settings

__all__ = ["with_retry", "install"]

HEALTH_PATH = "/api/v1/foundation/health"


def install(app: FastAPI) -> None:
    settings = get_settings()
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
    if settings.app_env == "test":
        return  # never rate-limit the test suite — see TESTS.md
    p24 = P24Settings()
    counter = build_counter(settings.redis_url)
    app.add_middleware(RateLimitMiddleware, counter=counter, limit=p24.rate_limit_per_minute,
                       window_seconds=p24.rate_limit_window_seconds, exempt_paths=frozenset({HEALTH_PATH}))
