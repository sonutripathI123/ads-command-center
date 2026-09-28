"""P21 — the business rules document and its chauffeur-business defaults.

Rules are versioned documents per scope: "global" (whole business) or "account:<ads_account_id>"
(overrides for one Google Ads account). Lists are lower-cased, trimmed and de-duplicated.
"""
from pydantic import BaseModel, Field, field_validator

DEFAULT_SERVICES = [
    "chauffeur", "chauffeured", "private driver", "driver service", "airport transfer", "airport transfers",
    "airport pickup", "airport chauffeur", "corporate car", "corporate cars", "corporate transfer", "executive car",
    "limo", "limousine", "luxury car hire", "car hire with driver", "wedding car", "wedding cars", "formal",
    "school formal", "event transfer", "cruise transfer", "hourly hire", "winery tour", "stretch limo", "sedan",
    "suv", "people mover", "van hire with driver",
]
DEFAULT_LOCATIONS = [
    "melbourne", "melbourne airport", "tullamarine", "avalon", "cbd", "southbank", "docklands", "st kilda",
    "geelong", "mornington", "yarra valley", "dandenong", "frankston", "box hill", "richmond", "south yarra",
    "port melbourne", "werribee", "victoria", "vic", "mcg",
]
DEFAULT_OTHER_LOCATIONS = [
    "sydney", "brisbane", "perth", "adelaide", "hobart", "canberra", "darwin", "gold coast", "cairns",
    "newcastle", "wollongong", "sunshine coast", "auckland", "nz", "new zealand", "london", "usa",
]
DEFAULT_EXCLUDED = [
    "job", "jobs", "career", "careers", "salary", "hiring", "vacancy", "vacancies", "employment", "course",
    "training", "licence", "license", "free", "cheap", "cheapest", "uber", "didi", "ola", "taxi", "cab",
    "bus", "skybus", "train", "tram", "shuttle bus", "public transport", "parking", "car rental", "rent a car",
    "self drive", "for sale", "buy", "second hand", "used", "toy", "game", "wikipedia", "meaning", "definition",
    "reddit", "how to become", "rideshare", "diy",
]


def _clean(values: list[str]) -> list[str]:
    seen, out = set(), []
    for v in values:
        v = " ".join(str(v).lower().split())
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


class Rules(BaseModel):
    services: list[str] = Field(default_factory=lambda: list(DEFAULT_SERVICES), max_length=500)
    locations: list[str] = Field(default_factory=lambda: list(DEFAULT_LOCATIONS), max_length=500)
    other_locations: list[str] = Field(default_factory=lambda: list(DEFAULT_OTHER_LOCATIONS), max_length=500,
                                       description="Places you do NOT serve")
    excluded_terms: list[str] = Field(default_factory=lambda: list(DEFAULT_EXCLUDED), max_length=1000,
                                      description="Words/phrases whose searches you never want")
    competitor_terms: list[str] = Field(default_factory=list, max_length=500)
    brand_terms: list[str] = Field(default_factory=list, max_length=100, description="Your own brand names")
    min_spend_for_negative: float = Field(default=20.0, ge=0, le=10_000)
    min_clicks_for_negative: int = Field(default=5, ge=1, le=1000)
    target_cost_per_conversion: float | None = Field(default=None, ge=0)
    notes: str = Field(default="", max_length=5000)

    @field_validator("services", "locations", "other_locations", "excluded_terms", "competitor_terms", "brand_terms")
    @classmethod
    def _norm(cls, v: list[str]) -> list[str]:
        return _clean(v)
