"""P04 — module-local settings (read from environment / backend/.env).

Shared secrets (OAuth client, developer token, APP_SECRET_KEY) come from app.shared.config.
"""
import base64
import hashlib
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.config import get_settings


class P04Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    google_ads_api_version: str = "v25"  # v26 answers "Method not found" (checked 2026-09-28)
    google_ads_oauth_redirect_uri: str = "http://localhost:8000/api/v1/ads-connection/oauth/callback"
    frontend_url: str = "http://localhost:3000"
    # Fernet key for refresh tokens at rest. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    credentials_encryption_key: SecretStr | None = None


@lru_cache
def get_p04_settings() -> P04Settings:
    return P04Settings()


def encryption_key() -> bytes:
    explicit = get_p04_settings().credentials_encryption_key
    if explicit:
        return explicit.get_secret_value().encode()
    shared = get_settings()
    if shared.is_production:
        raise RuntimeError("CREDENTIALS_ENCRYPTION_KEY must be set in production")
    # Development fallback: derive a stable key from APP_SECRET_KEY.
    digest = hashlib.sha256(b"p04-credentials:" + shared.app_secret_key.get_secret_value().encode()).digest()
    return base64.urlsafe_b64encode(digest)
