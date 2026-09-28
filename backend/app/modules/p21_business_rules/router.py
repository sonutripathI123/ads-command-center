"""P21 — routes under /api/v1/business-rules. Read: any signed-in user. Save/restore: approver or admin."""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p21_business_rules import service
from app.modules.p21_business_rules.rules import Rules
from app.shared.db import get_db

router = APIRouter()


class RulesOut(BaseModel):
    scope: str
    version: int
    is_default: bool
    rules: Rules
    updated_at: datetime | None
    updated_by: str | None
    note: str


class SaveIn(BaseModel):
    rules: Rules
    note: str = Field(default="", max_length=2000)


class VersionOut(BaseModel):
    version: int
    note: str
    created_by_email: str | None
    created_at: datetime


def _out(c: service.Current) -> RulesOut:
    return RulesOut(scope=c.scope, version=c.version, is_default=c.version == 0, rules=c.rules,
                    updated_at=c.updated_at, updated_by=c.updated_by, note=c.note)


@router.get("", response_model=RulesOut)
def get_rules(account_id: int | None = None, db: DbSession = Depends(get_db),
              _: CurrentUser = Depends(require_permission(Permission.READ))) -> RulesOut:
    return _out(service.current(db, service.scope_for(account_id)))


@router.get("/defaults", response_model=Rules)
def defaults(_: CurrentUser = Depends(require_permission(Permission.READ))) -> Rules:
    return Rules()


@router.put("", response_model=RulesOut, dependencies=[Depends(verify_origin)])
def save_rules(body: SaveIn, account_id: int | None = None, db: DbSession = Depends(get_db),
               user: CurrentUser = Depends(require_permission(Permission.APPROVE))) -> RulesOut:
    return _out(service.save(db, service.scope_for(account_id), body.rules, note=body.note, user_id=user.id, email=user.email))


@router.get("/versions", response_model=list[VersionOut])
def versions(account_id: int | None = None, db: DbSession = Depends(get_db),
             _: CurrentUser = Depends(require_permission(Permission.READ))) -> list[VersionOut]:
    return [VersionOut(version=v.version, note=v.note, created_by_email=v.created_by_email, created_at=v.created_at)
            for v in service.versions(db, service.scope_for(account_id))]


@router.post("/versions/{version}/restore", response_model=RulesOut, dependencies=[Depends(verify_origin)])
def restore(version: int, account_id: int | None = None, db: DbSession = Depends(get_db),
            user: CurrentUser = Depends(require_permission(Permission.APPROVE))) -> RulesOut:
    return _out(service.restore(db, service.scope_for(account_id), version, user_id=user.id, email=user.email))
