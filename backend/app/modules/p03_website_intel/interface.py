"""P03 — public interface (for P06 analytics, P07 audit, P10 landing pages/CRO, P11 competitors, P15 builder).

    from app.modules.p03_website_intel.interface import WebsiteRef, list_websites, website_pages, landing_pages
"""
import json
from dataclasses import dataclass

from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel import service

__all__ = ["WebsiteRef", "list_websites", "website_pages", "landing_pages"]


@dataclass(frozen=True)
class WebsiteRef:
    id: int
    name: str
    domain: str
    base_url: str
    primary_service: str
    location: str
    time_zone: str
    ads_account_id: int | None
    ga4_property_id: str | None
    gsc_site_url: str | None


def list_websites(db: DbSession) -> list[WebsiteRef]:
    return [WebsiteRef(id=w.id, name=w.name, domain=w.domain, base_url=w.base_url, primary_service=w.primary_service,
                       location=w.location, time_zone=w.time_zone, ads_account_id=w.ads_account_id,
                       ga4_property_id=w.ga4_property_id, gsc_site_url=w.gsc_site_url)
            for w in service.list_websites(db)]


def website_pages(db: DbSession, website_id: int) -> list[dict]:
    return [{"id": p.id, "url": p.url, "status_code": p.status_code, "title": p.title, "h1": p.h1,
             "word_count": p.word_count, "services": json.loads(p.services), "locations": json.loads(p.locations),
             "issues": json.loads(p.issues), "has_form": p.has_form, "has_phone": p.has_phone, "cta_count": p.cta_count}
            for p in service.pages(db, website_id)]


def landing_pages(db: DbSession, website_id: int) -> list[dict]:
    return service.landing_pages(db, website_id)
