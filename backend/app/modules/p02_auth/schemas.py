"""P02 — request/response contracts."""
from datetime import datetime

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=256)


class MeOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    permissions: list[str]


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    execute_enabled: bool
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserCreateIn(BaseModel):
    email: str = Field(max_length=255)
    name: str = Field(default="", max_length=255)
    role: str
    password: str = Field(max_length=256)


class UserUpdateIn(BaseModel):
    """Note: there is intentionally no execute_enabled field — execute can only be granted via the CLI."""

    name: str | None = Field(default=None, max_length=255)
    role: str | None = None
    is_active: bool | None = None


class RolesOut(BaseModel):
    roles: dict[str, list[str]]
