"""SHARED (owner: P00) — structured logging.

Every log line carries module_id and request_id. Modules get a logger with
get_logger("P08") and never configure handlers themselves.
Public interface: configure_logging, get_logger, request_id_var
"""
import json
import logging
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        if not hasattr(record, "module_id"):
            record.module_id = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "module_id": getattr(record, "module_id", None),
            "request_id": getattr(record, "request_id", None),
            "msg": record.getMessage(),
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in _RESERVED and k not in payload}
        if extras:
            payload["extra"] = extras
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter())
    handler.setFormatter(
        JsonFormatter() if json_output
        else logging.Formatter("%(asctime)s %(levelname)s [%(module_id)s] [%(request_id)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


class _ModuleAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("module_id", self.extra["module_id"])
        return msg, kwargs


def get_logger(module_id: str) -> logging.LoggerAdapter:
    return _ModuleAdapter(logging.getLogger(f"app.{module_id.lower()}"), {"module_id": module_id})
