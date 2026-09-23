"""SHARED (owner: P00) — application settings.

All configuration comes from environment variables (or backend/.env locally).
Secrets are typed as SecretStr so they never appear in logs or reprs.
Public interface: get_settings()
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", description="development | test | production")
    log_level: str = "INFO"
    log_json: bool = True

    database_url: str = "postgresql+psycopg://ads:ads@localhost:5432/ads_command_center"
    redis_url: str = "redis://localhost:6379/0"

    module_registry_path: Path = REPO_ROOT / "docs" / "modules.json"

    # Hard kill switch for any live Google Ads mutation. While true, every
    # kill_switch_guarded flag resolves to False regardless of DB overrides.
    # Only an operator changing the environment can lift it.
    ads_execution_kill_switch: bool = True

    # Secrets — consumed by later modules. Never log these.
    anthropic_api_key: SecretStr | None = None
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = None
    google_ads_developer_token: SecretStr | None = None
    google_ads_login_customer_id: str | None = None
    app_secret_key: SecretStr = SecretStr("dev-only-change-me")

    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.app_secret_key.get_secret_value() == "dev-only-change-me":
        raise RuntimeError("APP_SECRET_KEY must be set in production")
    return settings
