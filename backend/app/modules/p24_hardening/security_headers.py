"""P24 — standard security response headers (MID §11 P24: security review)."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, hsts: bool):
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if self.hsts:
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response
