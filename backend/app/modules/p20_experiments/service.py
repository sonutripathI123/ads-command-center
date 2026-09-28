"""P20 — experiment lifecycle and analysis. Experiments are measured from synced P05 data; any change needed to run one
(e.g. a new ad, a budget split) goes through P16 approval. Nothing is changed in Google Ads here."""
import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.p03_website_intel.interface import list_websites
from app.modules.p05_ads_sync.interface import ad_groups, ads, campaigns, list_accounts
from app.modules.p06_analytics.interface import tracking_health
from app.modules.p16_approvals.interface import get_approval, request_approval
from app.modules.p20_experiments import stats
from app.modules.p20_experiments.models import Experiment
from app.shared.errors import NotFoundError, ValidationFailed
from app.shared.logging import get_logger

MODULE_ID = "P20"
KINDS = ("a_b", "before_after")
ENTITY_TYPES = ("campaign", "ad_group", "ad")
METRIC_LABELS = {"ctr": "CTR", "conv_rate": "Conversion rate", "avg_cpc": "Avg. CPC", "cost_per_conversion": "Cost / conversion"}
EDITABLE = {"name", "hypothesis", "change_description", "primary_metric", "start_date", "end_date", "baseline_start",
            "baseline_end", "min_clicks", "control_ref", "variant_ref"}
log = get_logger(MODULE_ID)


def account(db: DbSession, account_id: int):
    a = next((a for a in list_accounts(db) if a.id == account_id), None)
    if a is None:
        raise NotFoundError("Google Ads account not found", module_id=MODULE_ID)
    return a


def entities(db: DbSession, account_id: int, entity_type: str, d1: date, d2: date) -> dict[str, dict]:
    if entity_type == "campaign":
        return {c["google_id"]: c | {"label": c["name"]} for c in campaigns(db, account_id, d1, d2)}
    if entity_type == "ad_group":
        return {g["google_id"]: g | {"label": f"{g['campaign_name']} › {g['name']}"} for g in ad_groups(db, account_id, d1, d2)}
    if entity_type == "ad":
        return {a["key"]: a | {"label": f"{a['ad_group_name']} › {(a['headlines'] or ['(no headline)'])[0]}"}
                for a in ads(db, account_id, d1, d2)}
    raise ValidationFailed(f"entity_type must be one of {ENTITY_TYPES}", module_id=MODULE_ID)


def _validate(db: DbSession, e: Experiment) -> None:
    def bad(msg):
        raise ValidationFailed(msg, module_id=MODULE_ID)

    if e.kind not in KINDS:
        bad(f"type must be one of {KINDS}")
    if e.primary_metric not in stats.METRICS:
        bad(f"primary metric must be one of {stats.METRICS}")
    if e.start_date > e.end_date:
        bad("Test period: start must be on or before end")
    if not 10 <= e.min_clicks <= 100_000:
        bad("Minimum clicks must be between 10 and 100000")
    known = entities(db, e.account_id, e.entity_type, e.start_date, e.start_date)
    if e.control_ref not in known:
        bad("Control not found in the synced account")
    if e.kind == "a_b":
        if not e.variant_ref or e.variant_ref not in known:
            bad("Variant not found in the synced account")
        if e.variant_ref == e.control_ref:
            bad("Control and variant must be different")
        e.baseline_start = e.baseline_end = None
    else:
        e.variant_ref = None
        if not e.baseline_start or not e.baseline_end or e.baseline_start > e.baseline_end:
            bad("Before/after needs a baseline period (start on or before end)")
        if e.baseline_end >= e.start_date:
            bad("Baseline period must end before the test period starts")


def create(db: DbSession, account_id: int, data: dict, *, by: str) -> Experiment:
    account(db, account_id)
    e = Experiment(account_id=account_id, created_by=by, **data)
    _validate(db, e)
    db.add(e)
    db.commit()
    return e


def get(db: DbSession, experiment_id: int) -> Experiment:
    e = db.get(Experiment, experiment_id)
    if e is None:
        raise NotFoundError("Experiment not found", module_id=MODULE_ID)
    return e


def list_experiments(db: DbSession, account_id: int) -> list[Experiment]:
    return list(db.scalars(select(Experiment).where(Experiment.account_id == account_id).order_by(Experiment.id.desc())))


def edit(db: DbSession, experiment_id: int, changes: dict) -> Experiment:
    e = get(db, experiment_id)
    if e.status != "draft":
        raise ValidationFailed("Only draft experiments can be edited", module_id=MODULE_ID)
    for k, v in changes.items():
        if k not in EDITABLE:
            raise ValidationFailed(f"'{k}' cannot be edited", module_id=MODULE_ID)
        setattr(e, k, v)
    _validate(db, e)
    db.commit()
    return e


def _label(db: DbSession, e: Experiment, ref: str | None) -> str | None:
    if ref is None:
        return None
    return entities(db, e.account_id, e.entity_type, e.start_date, e.start_date).get(ref, {}).get("label", ref)


def submit(db: DbSession, experiment_id: int, *, by: str) -> Experiment:
    """Ask P16 for approval to run the experiment (the user makes/approves the change it tests)."""
    e = get(db, experiment_id)
    if e.status != "draft":
        raise ValidationFailed("Only draft experiments can be submitted", module_id=MODULE_ID)
    period = f"{e.start_date} → {e.end_date}"
    a = request_approval(
        db, account_id=e.account_id, source_module=MODULE_ID, source_ref=f"P20|experiment|{e.id}",
        change_type="start_experiment", title=f"Run experiment '{e.name}'",
        before={"control": _label(db, e, e.control_ref), **({"baseline": f"{e.baseline_start} → {e.baseline_end}"}
                                                             if e.kind == "before_after" else {})},
        after={"change": e.change_description or "(none described)", "test_period": period,
               **({"variant": _label(db, e, e.variant_ref)} if e.kind == "a_b" else {})},
        evidence=[["Hypothesis", e.hypothesis or "—"], ["Primary metric", METRIC_LABELS[e.primary_metric]],
                  ["Minimum clicks per side", str(e.min_clicks)]],
        risk="low", payload={"experiment_id": e.id, "kind": e.kind, "entity_type": e.entity_type}, requested_by=by)
    e.status, e.approval_id = "pending_approval", a["id"]
    db.commit()
    return e


def approval_state(db: DbSession, e: Experiment) -> str | None:
    a = get_approval(db, e.approval_id) if e.approval_id else None
    return a["status"] if a else None


def start(db: DbSession, experiment_id: int) -> Experiment:
    e = get(db, experiment_id)
    if e.status != "pending_approval":
        raise ValidationFailed("Submit the experiment for approval first", module_id=MODULE_ID)
    st = approval_state(db, e)
    if st in ("rejected", "withdrawn"):
        e.status = "draft"
        db.commit()
        raise ValidationFailed(f"The approval was {st}; the experiment is back in draft", module_id=MODULE_ID)
    if st not in ("approved", "executed"):
        raise ValidationFailed("Waiting for approval in the Approval Center", module_id=MODULE_ID)
    e.status = "running"
    db.commit()
    return e


def _tracking_issues(db: DbSession, account_id: int, d1: date, d2: date) -> list[str]:
    site = next((w for w in list_websites(db) if w.ads_account_id == account_id), None)
    if site is None:
        return ["No website is linked to this Google Ads account, so conversion tracking could not be checked."]
    try:
        return [h["title"] for h in tracking_health(db, site.id, d1, d2) if h["severity"] == "critical"]
    except Exception:  # noqa: BLE001 — health is a caveat, never a blocker
        log.warning("tracking_health_failed", extra={"account_id": account_id})
        return []


def analyze(db: DbSession, experiment_id: int, *, today: date | None = None) -> dict:
    e = get(db, experiment_id)
    today = today or date.today()
    end = min(e.end_date, today)
    if e.start_date > today:
        raise ValidationFailed("The test period has not started yet", module_id=MODULE_ID)
    test = entities(db, e.account_id, e.entity_type, e.start_date, end)
    if e.kind == "a_b":
        control, variant = test.get(e.control_ref), test.get(e.variant_ref)
        periods = {"control": [e.start_date, end], "variant": [e.start_date, end]}
    else:
        base = entities(db, e.account_id, e.entity_type, e.baseline_start, e.baseline_end)
        control, variant = base.get(e.control_ref), test.get(e.control_ref)
        periods = {"control": [e.baseline_start, e.baseline_end], "variant": [e.start_date, end]}
    if control is None or variant is None:
        raise ValidationFailed("The entity is no longer in the synced account", module_id=MODULE_ID)
    cmp = stats.compare(control, variant, primary=e.primary_metric, min_clicks=e.min_clicks)
    limits = []
    if not cmp["enough_data"]:
        limits.append(f"Fewer than {e.min_clicks} clicks on one side ({control['clicks']} vs {variant['clicks']}) — "
                      "keep the test running before deciding.")
    if e.end_date > today:
        limits.append(f"Test period is not finished (ends {e.end_date}); results so far cover up to {end}.")
    issues = _tracking_issues(db, e.account_id, periods["control"][0], end)
    if issues:
        limits.append("Conversion tracking has critical issues (" + "; ".join(issues[:3]) +
                      ") — conversion rate and cost/conversion are not reliable.")
    if e.kind == "before_after":
        limits.append("Before/after compares different dates: seasonality, competitor activity and any other account "
                      "changes in between also affect the result. Treat it as evidence, not proof.")
        days = [(p[1] - p[0]).days + 1 for p in periods.values()]
        if days[0] != days[1]:
            limits.append(f"Periods have different lengths ({days[0]} vs {days[1]} days) — compare rates, not totals.")
    if control["clicks"] == 0 and variant["clicks"] == 0:
        limits.append("No clicks in either period — is the campaign paused or the data not synced?")
    res = {"computed_on": today.isoformat(), "periods": {k: [str(v[0]), str(v[1])] for k, v in periods.items()},
           "control": {"label": control["label"], **{k: control[k] for k in ("impressions", "clicks", "cost", "conversions")}},
           "variant": {"label": variant["label"], **{k: variant[k] for k in ("impressions", "clicks", "cost", "conversions")}},
           **cmp, "primary_metric": e.primary_metric, "limitations": limits}
    if e.status in ("running", "completed"):
        e.results = json.dumps(res, default=str)
        db.commit()
    return res


def complete(db: DbSession, experiment_id: int, conclusion: str) -> Experiment:
    e = get(db, experiment_id)
    if e.status != "running":
        raise ValidationFailed("Only running experiments can be completed", module_id=MODULE_ID)
    if not conclusion.strip():
        raise ValidationFailed("Write the conclusion (what you learned / will do next)", module_id=MODULE_ID)
    analyze(db, experiment_id)
    e.status, e.conclusion = "completed", conclusion.strip()
    db.commit()
    return e


def cancel(db: DbSession, experiment_id: int) -> Experiment:
    e = get(db, experiment_id)
    if e.status in ("completed", "cancelled"):
        raise ValidationFailed(f"Experiment is already {e.status}", module_id=MODULE_ID)
    e.status = "cancelled"
    db.commit()
    return e


def experiment_dict(db: DbSession, e: Experiment) -> dict:
    return {"id": e.id, "account_id": e.account_id, "name": e.name, "hypothesis": e.hypothesis,
            "change_description": e.change_description, "kind": e.kind, "entity_type": e.entity_type,
            "control_ref": e.control_ref, "control_label": _label(db, e, e.control_ref), "variant_ref": e.variant_ref,
            "variant_label": _label(db, e, e.variant_ref), "primary_metric": e.primary_metric, "baseline_start": e.baseline_start,
            "baseline_end": e.baseline_end, "start_date": e.start_date, "end_date": e.end_date, "min_clicks": e.min_clicks,
            "status": e.status, "approval_id": e.approval_id, "approval_status": approval_state(db, e),
            "results": json.loads(e.results) if e.results else None, "conclusion": e.conclusion,
            "created_by": e.created_by, "created_at": e.created_at, "updated_at": e.updated_at}
