"""P20 — routes under /api/v1/experiments. Measurement only; running an experiment needs a P16 approval."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p05_ads_sync.interface import list_accounts
from app.modules.p20_experiments import service, stats
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))
RECOMMEND = Depends(require_permission(Permission.RECOMMEND))


class ExperimentIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    hypothesis: str = Field(default="", max_length=4000)
    change_description: str = Field(default="", max_length=4000)
    kind: str
    entity_type: str
    control_ref: str = Field(min_length=1, max_length=128)
    variant_ref: str | None = Field(default=None, max_length=128)
    primary_metric: str = "ctr"
    baseline_start: date | None = None
    baseline_end: date | None = None
    start_date: date
    end_date: date
    min_clicks: int = 100


class EditIn(BaseModel):
    model_config = {"extra": "allow"}


class ConcludeIn(BaseModel):
    conclusion: str = Field(max_length=4000)


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return [{"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name} for a in list_accounts(db)]


@router.get("/meta")
def meta(_: CurrentUser = READ) -> dict:
    return {"kinds": list(service.KINDS), "entity_types": list(service.ENTITY_TYPES),
            "metrics": [{"key": k, "label": v, "tested": k in stats.RATE_METRICS} for k, v in service.METRIC_LABELS.items()]}


@router.get("/accounts/{account_id}/entities")
def entity_options(account_id: int, entity_type: str = Query(...), db: DbSession = Depends(get_db),
                   _: CurrentUser = READ) -> list[dict]:
    service.account(db, account_id)
    d2 = date.today()
    ents = service.entities(db, account_id, entity_type, d2 - timedelta(days=89), d2)
    return sorted([{"ref": k, "label": v["label"], "status": v["status"], "clicks_90d": v["clicks"]} for k, v in ents.items()],
                  key=lambda x: -x["clicks_90d"])


@router.post("/accounts/{account_id}", status_code=201, dependencies=[Depends(verify_origin)])
def create(account_id: int, body: ExperimentIn, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    return service.experiment_dict(db, service.create(db, account_id, body.model_dump(), by=user.email))


@router.get("/accounts/{account_id}")
def list_(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.account(db, account_id)
    return [service.experiment_dict(db, e) for e in service.list_experiments(db, account_id)]


@router.get("/{experiment_id}")
def get(experiment_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.experiment_dict(db, service.get(db, experiment_id))


@router.patch("/{experiment_id}", dependencies=[Depends(verify_origin)])
def edit(experiment_id: int, body: EditIn, db: DbSession = Depends(get_db), _: CurrentUser = RECOMMEND) -> dict:
    changes = body.model_dump()
    for k in ("start_date", "end_date", "baseline_start", "baseline_end"):
        if changes.get(k):
            changes[k] = date.fromisoformat(changes[k])
    return service.experiment_dict(db, service.edit(db, experiment_id, changes))


@router.post("/{experiment_id}/submit", dependencies=[Depends(verify_origin)])
def submit(experiment_id: int, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    return service.experiment_dict(db, service.submit(db, experiment_id, by=user.email))


@router.post("/{experiment_id}/start", dependencies=[Depends(verify_origin)])
def start(experiment_id: int, db: DbSession = Depends(get_db), _: CurrentUser = RECOMMEND) -> dict:
    return service.experiment_dict(db, service.start(db, experiment_id))


@router.post("/{experiment_id}/analyze", dependencies=[Depends(verify_origin)])
def analyze(experiment_id: int, db: DbSession = Depends(get_db), _: CurrentUser = RECOMMEND) -> dict:
    return service.analyze(db, experiment_id)


@router.post("/{experiment_id}/complete", dependencies=[Depends(verify_origin)])
def complete(experiment_id: int, body: ConcludeIn, db: DbSession = Depends(get_db), _: CurrentUser = RECOMMEND) -> dict:
    return service.experiment_dict(db, service.complete(db, experiment_id, body.conclusion))


@router.post("/{experiment_id}/cancel", dependencies=[Depends(verify_origin)])
def cancel(experiment_id: int, db: DbSession = Depends(get_db), _: CurrentUser = RECOMMEND) -> dict:
    return service.experiment_dict(db, service.cancel(db, experiment_id))
