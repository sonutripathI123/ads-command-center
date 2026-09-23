"""P04 — request/response contracts. Refresh tokens never appear in any response."""
from datetime import datetime

from pydantic import BaseModel


class ConnectionOut(BaseModel):
    id: int
    google_email: str | None
    status: str
    last_checked_at: datetime | None
    last_error: str | None
    created_at: datetime


class AccountOut(BaseModel):
    id: int
    customer_id: str
    descriptive_name: str
    currency_code: str | None
    time_zone: str | None
    is_manager: bool
    is_test_account: bool
    login_customer_id: str | None
    connection_id: int
    status: str
    added_at: datetime


class StatusOut(BaseModel):
    oauth_client_configured: bool
    developer_token_configured: bool
    api_version: str
    redirect_uri: str
    connections: list[ConnectionOut]
    accounts: list[AccountOut]


class DiscoveredOut(BaseModel):
    customer_id: str
    descriptive_name: str
    currency_code: str | None
    time_zone: str | None
    is_manager: bool
    is_test_account: bool
    status: str | None
    login_customer_id: str | None
    already_added: bool


class CheckOut(BaseModel):
    connection: ConnectionOut
    accessible_customer_ids: list[str]


class AddAccountIn(BaseModel):
    connection_id: int
    customer_id: str
    login_customer_id: str | None = None


class AccountStatusIn(BaseModel):
    status: str
