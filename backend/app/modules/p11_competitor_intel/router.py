"""P11 — routes under /api/v1/competitors. Public-website research needs flag competitor.research.enabled."""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.modules.p02_auth.interface import CurrentUser, Permission, require_permission, verify_origin
from app.modules.p11_competitor_intel import service
from app.shared.db import get_db

router = APIRouter()
READ = Depends(require_permission(Permission.READ))
RECOMMEND = Depends(require_permission(Permission.RECOMMEND))


class CompetitorIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website: str = Field(min_length=3, max_length=512)
    brand_terms: list[str] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=4000)


class CompetitorEdit(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    brand_terms: list[str] | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=4000)
    status: str | None = None


class ObservationIn(BaseModel):
    kind: str
    query: str | None = Field(default=None, max_length=200)
    placement: str | None = None
    position: int | None = None
    text: str | None = Field(default=None, max_length=2000)
    device: str | None = Field(default=None, max_length=20)
    location: str | None = Field(default=None, max_length=100)
    observed_on: date | None = None


class AnalyzeIn(BaseModel):
    use_ai: bool = True


@router.get("/accounts")
def accounts(db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    return [{"id": a.id, "customer_id": a.customer_id, "name": a.descriptive_name, "competitors": len(service.competitors(db, a.id))}
            for a in service.list_accounts(db)]


@router.get("/accounts/{account_id}")
def overview(account_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> dict:
    return service.overview(db, account_id) | {"analysis": service.analysis_dict(service.latest_analysis(db, account_id))}


@router.post("/accounts/{account_id}/competitors", status_code=201, dependencies=[Depends(verify_origin)])
def add(account_id: int, body: CompetitorIn, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    c = service.add_competitor(db, account_id, name=body.name, website=body.website, brand_terms=body.brand_terms,
                               notes=body.notes, by=user.email)
    return {"id": c.id, "name": c.name, "domain": c.domain}


@router.patch("/competitors/{competitor_id}", dependencies=[Depends(verify_origin)])
def edit(competitor_id: int, body: CompetitorEdit, db: DbSession = Depends(get_db), _: CurrentUser = RECOMMEND) -> dict:
    c = service.update_competitor(db, competitor_id, body.model_dump())
    return {"id": c.id, "name": c.name, "status": c.status}


@router.post("/competitors/{competitor_id}/research", dependencies=[Depends(verify_origin)])
def research(competitor_id: int, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    return service.run_research(db, competitor_id, by=user.email)


@router.post("/competitors/{competitor_id}/observations", status_code=201, dependencies=[Depends(verify_origin)])
def observe(competitor_id: int, body: ObservationIn, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    data = body.model_dump(exclude={"kind", "observed_on"}, exclude_none=True)
    o = service.add_observation(db, competitor_id, kind=body.kind, data=data, observed_on=body.observed_on or date.today(), by=user.email)
    return {"id": o.id}


@router.delete("/observations/{observation_id}", status_code=204, dependencies=[Depends(verify_origin)])
def delete_observation(observation_id: int, db: DbSession = Depends(get_db), _: CurrentUser = RECOMMEND) -> None:
    service.delete_observation(db, observation_id)


@router.get("/competitors/{competitor_id}/pages")
def pages(competitor_id: int, db: DbSession = Depends(get_db), _: CurrentUser = READ) -> list[dict]:
    service.get(db, competitor_id)
    return [o | {"data": {k: v for k, v in o["data"].items() if k != "text"}}
            for o in service.observations(db, [competitor_id]) if o["kind"] == "page"]


@router.post("/accounts/{account_id}/analyze", status_code=201, dependencies=[Depends(verify_origin)])
def analyze(account_id: int, body: AnalyzeIn, db: DbSession = Depends(get_db), user: CurrentUser = RECOMMEND) -> dict:
    return service.analysis_dict(service.analyze(db, account_id, use_ai=body.use_ai, by=user.email))
