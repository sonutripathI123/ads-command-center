"""P17 — turns an APPROVED P16 change into the exact Google Ads REST request(s) it would send. Pure: no DB, no network.

Supported today (everything else must be applied by hand — the plan says so):
  add_negative_keywords  -> campaignCriteria:mutate  (campaign-level negatives; account-level ones are applied to
                            every non-removed campaign, because account-level keyword negatives aren't used here)
  create_rsa             -> adGroupAds:mutate        (always created PAUSED)
Rollback = the matching `remove` operations for the resource names Google returned.
"""
import hashlib
import json
from dataclasses import dataclass

MAX_OPERATIONS = 500
SUPPORTED = ("add_negative_keywords", "create_rsa")
MATCH = {"EXACT": "EXACT", "PHRASE": "PHRASE", "BROAD": "BROAD"}


class PlanError(ValueError):
    """The approved change can't be turned into a safe, complete request (reason is user-facing)."""


@dataclass(frozen=True)
class Operation:
    service: str          # e.g. "campaignCriteria" -> POST .../customers/{id}/campaignCriteria:mutate
    label: str
    operations: tuple     # Google "operations" array entries (create/remove)

    def body(self, *, validate_only: bool) -> dict:
        return {"operations": list(self.operations), "partialFailure": False, "validateOnly": validate_only}

    def preview(self) -> dict:
        return {"service": self.service, "label": self.label, "count": len(self.operations),
                "sample": list(self.operations[:3])}


def plan_hash(ops: list[Operation]) -> str:
    canon = json.dumps([{"s": o.service, "o": list(o.operations)} for o in ops], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def _rn(customer_id: str, kind: str, gid: str) -> str:
    if not (str(gid).isdigit() and str(customer_id).isdigit()):
        raise PlanError(f"Invalid Google id '{gid}'.")
    return f"customers/{customer_id}/{kind}/{gid}"


def negatives_plan(customer_id: str, negatives: list[dict], campaigns: list[dict]) -> list[Operation]:
    if not negatives:
        raise PlanError("The approval contains no negative keywords.")
    live = [str(c["google_id"]) for c in campaigns if (c.get("status") or "").upper() != "REMOVED"]
    seen, ops = set(), []
    for n in negatives:
        text = (n.get("text") or "").strip()
        mt = MATCH.get((n.get("match_type") or "").upper())
        if not text or mt is None:
            raise PlanError(f"Negative keyword '{text or '?'}' has no valid match type.")
        targets = [str(n["campaign_id"])] if n.get("campaign_id") else live
        if not targets:
            raise PlanError("No campaigns synced for this account — sync Google Ads first.")
        for cid in targets:
            key = (cid, text.lower(), mt)
            if key in seen:
                continue
            seen.add(key)
            ops.append({"create": {"campaign": _rn(customer_id, "campaigns", cid), "negative": True,
                                   "keyword": {"text": text, "matchType": mt}}})
    if len(ops) > MAX_OPERATIONS:
        raise PlanError(f"{len(ops)} operations is over the safety cap of {MAX_OPERATIONS}; split the batch.")
    return [Operation("campaignCriteria", f"Add {len(ops)} negative keyword(s) to campaigns", tuple(ops))]


def rsa_plan(customer_id: str, approved: dict, draft: dict) -> list[Operation]:
    """`approved` = what the human approved (P16 `after`); `draft` = the live P09 draft (must still match)."""
    if not draft.get("ad_group_google_id"):
        raise PlanError("This draft isn't linked to an existing Google Ads ad group — use the Google Ads Editor export instead.")
    for k in ("headlines", "descriptions", "final_url"):
        if approved.get(k) != draft.get(k):
            raise PlanError(f"The ad draft changed after it was approved ({k}). Withdraw and re-approve it.")
    heads, descs = approved["headlines"], approved["descriptions"]
    if not (3 <= len(heads) <= 15 and 2 <= len(descs) <= 4):
        raise PlanError("An RSA needs 3–15 headlines and 2–4 descriptions.")
    ad = {"finalUrls": [approved["final_url"]],
          "responsiveSearchAd": {"headlines": [{"text": h} for h in heads], "descriptions": [{"text": d} for d in descs]}}
    paths = [p for p in approved.get("paths", []) if p]
    if paths:
        ad["responsiveSearchAd"]["path1"] = paths[0]
        if len(paths) > 1:
            ad["responsiveSearchAd"]["path2"] = paths[1]
    op = {"create": {"adGroup": _rn(customer_id, "adGroups", str(draft["ad_group_google_id"])), "status": "PAUSED", "ad": ad}}
    return [Operation("adGroupAds", f"Add a PAUSED responsive search ad to '{draft.get('ad_group_name', '')}'", (op,))]


def rollback_plan(service: str, resource_names: list[str]) -> list[Operation]:
    if not resource_names:
        raise PlanError("Nothing to roll back — Google returned no resource names.")
    return [Operation(service, f"Remove {len(resource_names)} item(s) created by the execution",
                      tuple({"remove": rn} for rn in resource_names))]
