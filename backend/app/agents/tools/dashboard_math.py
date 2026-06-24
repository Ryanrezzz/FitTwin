"""Deterministic dashboard metrics — pure, reproducible Python (no LLM).

The dashboard's overview cards are *derived on read* from the profile + active
plan (+ today's log once logging lands). Keeping the arithmetic here — not on the
client and not in a model — is the same reliability rule as nutrition_math: any
number a user acts on comes from a tested tool.
"""
from __future__ import annotations

import math

from app.agents.tools import nutrition_math as nm
from app.domain import ActivityLevel, Goal, Sex

# Daily step goal by self-reported activity level.
STEP_GOAL: dict[ActivityLevel, int] = {
    ActivityLevel.sedentary: 6000,
    ActivityLevel.light: 7500,
    ActivityLevel.moderate: 9000,
    ActivityLevel.active: 10000,
    ActivityLevel.very_active: 12000,
}
WATER_ML_PER_KG = 35          # ~35 ml/kg bodyweight/day, rounded to 50 ml
HEALTHY_BMI = 22.0            # mid healthy-range BMI → target-weight reference
MAX_PROJECTION_WEEKS = 104    # don't project goals more than ~2 years out


def healthy_target_weight(height_cm: float, weight_kg: float, goal: Goal) -> float:
    """A healthy-BMI (22) target, clamped so direction matches the goal.

    lose → never above current; gain → never below current; maintain → current.
    """
    if height_cm <= 0:
        return round(weight_kg, 1)
    healthy = HEALTHY_BMI * (height_cm / 100.0) ** 2
    if goal == Goal.lose:
        return round(min(healthy, weight_kg), 1)
    if goal == Goal.gain:
        return round(max(healthy, weight_kg), 1)
    return round(weight_kg, 1)


def water_goal_ml(weight_kg: float) -> int:
    return int(round(WATER_ML_PER_KG * weight_kg / 50.0) * 50)


def step_goal(activity_level: ActivityLevel) -> int:
    return STEP_GOAL.get(activity_level, 9000)


def weeks_to_goal(weight_kg: float, target_kg: float, rate_kg_per_week: float) -> int | None:
    """Whole weeks to reach the target at the planned rate, or None if N/A."""
    delta = abs(weight_kg - target_kg)
    if rate_kg_per_week <= 0 or delta < 0.1:
        return None
    return min(int(math.ceil(delta / rate_kg_per_week)), MAX_PROJECTION_WEEKS)


def _pct(part: float, whole: float) -> int:
    return int(round(part / whole * 100)) if whole > 0 else 0


def dashboard_summary(profile: dict, plan: dict | None, today: dict | None = None) -> dict:
    """Compute the overview-card values from profile + active plan (+ today's log).

    `plan` is the active plan's targets ({calorie_target, macros}); when absent we
    derive targets from the profile so the dashboard is useful before generation.
    `today` is the current day's log (calories/protein/steps/water_ml/workout_done)
    — defaults to an empty day until daily logging is implemented.
    """
    today = today or {}
    weight = float(profile["weight_kg"])
    goal = Goal(profile["goal"])
    activity = ActivityLevel(profile["activity_level"])
    target_weight = healthy_target_weight(profile["height_cm"], weight, goal)

    if plan:
        calorie_target = int(plan["calorie_target"])
        protein_target = int(plan["macros"]["protein_g"])
    else:
        t = nm.full_targets(
            sex=Sex(profile["sex"]),
            weight_kg=weight,
            height_cm=profile["height_cm"],
            age=profile["age"],
            activity_level=activity,
            goal=goal,
            rate_kg_per_week=profile.get("rate_kg_per_week", 0.5),
        )
        calorie_target = t["calories"]
        protein_target = t["macros"]["protein_g"]

    cals_today = int(today.get("calories", 0) or 0)
    protein_today = int(today.get("protein_g", 0) or 0)
    water_today = int(today.get("water_ml", 0) or 0)
    steps_today = int(today.get("steps", 0) or 0)

    workout_target_days = int(profile.get("training_days", 0) or 0)
    workouts_done = int(today.get("workouts_done_week", 0) or 0)
    rate = profile.get("rate_kg_per_week", 0.5)

    return {
        "goal": goal.value,
        "current_weight_kg": round(weight, 1),
        "target_weight_kg": target_weight,
        "est_goal_weeks": weeks_to_goal(weight, target_weight, rate),
        "calorie_target": calorie_target,
        "calories_remaining": max(calorie_target - cals_today, 0),
        "protein_target_g": protein_target,
        "protein_remaining_g": max(protein_target - protein_today, 0),
        "water_goal_ml": water_goal_ml(weight),
        "water_ml": water_today,
        "step_goal": step_goal(activity),
        "steps": steps_today,
        "workout_target_days": workout_target_days,
        "workouts_done": workouts_done,
        "workout_completion_pct": _pct(workouts_done, workout_target_days),
        "streak_days": int(today.get("streak_days", 0) or 0),
    }
