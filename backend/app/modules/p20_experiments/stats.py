"""P20 — pure comparison maths. Rates (CTR, conversion rate) get a two-proportion z-test; cost metrics are directional only."""
import math

RATE_METRICS = {"ctr": ("clicks", "impressions"), "conv_rate": ("conversions", "clicks")}
COST_METRICS = {"avg_cpc", "cost_per_conversion"}
METRICS = [*RATE_METRICS, *COST_METRICS]
LOWER_IS_BETTER = COST_METRICS
ALPHA = 0.05


def two_proportion(x1: float, n1: float, x2: float, n2: float) -> float | None:
    """Two-sided p-value for H0: p1 == p2. None when a group is empty or the pooled rate is 0/1."""
    if n1 <= 0 or n2 <= 0:
        return None
    p = (x1 + x2) / (n1 + n2)
    if p <= 0 or p >= 1:
        return None
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (x2 / n2 - x1 / n1) / se
    return math.erfc(abs(z) / math.sqrt(2))


def _lift(a: float | None, b: float | None) -> float | None:
    return round((b - a) / a, 4) if a not in (None, 0) and b is not None else None


def compare(control: dict, variant: dict, *, primary: str, min_clicks: int) -> dict:
    """control/variant are P05 metric dicts. Returns per-metric rows + a verdict on the primary metric."""
    rows = []
    for m in METRICS:
        a, b = control.get(m), variant.get(m)
        row = {"metric": m, "control": a, "variant": b, "lift": _lift(a, b), "p_value": None, "test": "directional"}
        if m in RATE_METRICS:
            num, den = RATE_METRICS[m]
            p = two_proportion(control[num], control[den], variant[num], variant[den])
            row |= {"p_value": round(p, 4) if p is not None else None, "test": "two-proportion z-test"}
        if row["lift"] is not None:
            better = row["lift"] < 0 if m in LOWER_IS_BETTER else row["lift"] > 0
            row["direction"] = "better" if better else ("same" if row["lift"] == 0 else "worse")
        rows.append(row)
    enough = min(control["clicks"], variant["clicks"]) >= min_clicks
    main = next(r for r in rows if r["metric"] == primary)
    if not enough:
        verdict = "insufficient_data"
    elif main["lift"] is None:
        verdict = "insufficient_data"
    elif primary in RATE_METRICS:
        verdict = ("variant_better" if main["direction"] == "better" else "control_better") \
            if main["p_value"] is not None and main["p_value"] < ALPHA else "no_significant_difference"
    else:
        verdict = "directional_" + ("variant_better" if main["direction"] == "better" else "control_better")
    return {"rows": rows, "verdict": verdict, "enough_data": enough}
