"""P04 — tables: connections (Google OAuth grants), ads_accounts (accounts added to the dashboard)."""
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="google_ads")
    google_email: Mapped[str | None] = mapped_column(String(255))
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)  # Fernet ciphertext; NULL once revoked
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # active | error | revoked
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class AdsAccount(Base):
    __tablename__ = "ads_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    descriptive_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    currency_code: Mapped[str | None] = mapped_column(String(3))
    time_zone: Mapped[str | None] = mapped_column(String(64))
    is_manager: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_test_account: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    login_customer_id: Mapped[str | None] = mapped_column(String(10))
    connection_id: Mapped[int] = mapped_column(ForeignKey("connections.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # active | disabled
    added_by_user_id: Mapped[int | None] = mapped_column(Integer)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
