"""Deterministic progress analytics — the brain behind weekly adaptation.

Plateau detection must be *explainable and consistent*, never a vibe from an
LLM. Weight is noisy (water/glycogen), so we smooth with EWMA and estimate the
underlying trend with least-squares regression.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain import Goal


@dataclass(frozen=True)
class Trend:
    slope_kg_per_week: float
    ewma_latest: float
    n_points: int


def _to_day_offsets(series: list[tuple]) -> tuple[list[float], list[float]]:
    """Accept [(date|int, weight), ...] -> (x_days_from_start, y_weights)."""
    if not series:
        return [], []
    keys = [p[0] for p in series]
    weights = [float(p[1]) for p in series]
    if isinstance(keys[0], date):
        base = keys[0].toordinal()
        xs = [float(k.toordinal() - base) for k in keys]
    else:
        xs = [float(k) for k in keys]
    return xs, weights


def _linreg_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else 0.0


def ewma(values: list[float], alpha: float = 0.3) -> float:
    """Exponentially-weighted moving average — kills daily water-weight noise."""
    if not values:
        return 0.0
    s = values[0]
    for v in values[1:]:
        s = alpha * v + (1 - alpha) * s
    return s


def weight_trend(series: list[tuple]) -> Trend:
    """Estimate weekly weight change from a (date, weight) series."""
    xs, ys = _to_day_offsets(series)
    slope_per_day = _linreg_slope(xs, ys)
    return Trend(
        slope_kg_per_week=round(slope_per_day * 7, 3),
        ewma_latest=round(ewma(ys), 2),
        n_points=len(ys),
    )


def plateau_detected(
    trend: Trend,
    goal: Goal,
    adherence_pct: float,
    *,
    min_points: int = 7,
    slope_threshold_kg_wk: float = 0.1,
) -> bool:
    """A plateau = sticking to the plan but not moving in the goal direction.

    Crucially, low adherence is NOT a plateau (the fix is "follow the plan",
    not "change the plan"). Maintenance goals never plateau.
    """
    if goal == Goal.maintain:
        return False
    if trend.n_points < min_points:
        return False            # not enough data to call it
    if adherence_pct < 70:
        return False            # adherence problem, not a true plateau
    direction = -1.0 if goal == Goal.lose else 1.0
    progress = trend.slope_kg_per_week * direction   # >0 means moving correctly
    return progress < slope_threshold_kg_wk


def adherence(logs: list[dict], plan: dict, *, cal_tolerance: float = 0.10) -> float:
    """Percent of logged days within calorie band AND hitting >=90% protein.

    logs: [{calories, protein_g, ...}], plan: {calorie_target, macros:{protein_g}}
    Returns 0..100. No logs -> 0.0.
    """
    if not logs:
        return 0.0
    target_cals = plan.get("calorie_target", 0)
    target_protein = plan.get("macros", {}).get("protein_g", 0)
    if target_cals <= 0:
        return 0.0
    lo, hi = target_cals * (1 - cal_tolerance), target_cals * (1 + cal_tolerance)
    adherent = 0
    for log in logs:
        cals_ok = lo <= log.get("calories", 0) <= hi
        protein_ok = log.get("protein_g", 0) >= 0.9 * target_protein
        if cals_ok and protein_ok:
            adherent += 1
    return round(100 * adherent / len(logs), 1)
