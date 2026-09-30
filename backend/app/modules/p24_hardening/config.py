"""P24 — module-local settings (env-driven, all optional with safe defaults)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class P24Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    rate_limit_per_minute: int = 300
    rate_limit_window_seconds: int = 60
