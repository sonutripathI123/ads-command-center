"""SHARED (owner: P00) — application factory.

Do not add module routes here. Each active module in docs/modules.json exposes
`router` in app/modules/<package>/router.py and is mounted automatically at its api_prefix.
"""
import importlib
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.modules.p24_hardening.interface import install as install_hardening
from app.shared.config import get_settings
from app.shared.errors import register_error_handlers
from app.shared.logging import configure_logging, get_logger, request_id_var
from app.shared.registry import load_registry

log = get_logger("P00")


def mount_modules(app: FastAPI) -> list[str]:
    mounted = []
    for spec in load_registry().modules:
        if not spec.is_active or spec.api_prefix is None:
            continue
        module = importlib.import_module(f"app.modules.{spec.package}.router")
        app.include_router(module.router, prefix=spec.api_prefix, tags=[f"{spec.id} {spec.name}"])
        mounted.append(spec.id)
    return mounted


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(title="AI Google Ads Specialist", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def _request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["x-request-id"] = rid
        return response

    register_error_handlers(app)
    install_hardening(app)  # P24: rate limiting + security headers (see p24_hardening/CHANGELOG.md)
    mounted = mount_modules(app)
    log.info("app_started", extra={"env": settings.app_env, "modules": mounted,
                                   "execution_kill_switch": settings.ads_execution_kill_switch})
    return app


app = create_app()
