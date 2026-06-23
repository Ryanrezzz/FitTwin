"""Deterministic nutrition math — the numbers a user could be harmed by.

NONE of this is done by an LLM. Pure, reproducible, unit-tested Python.
References: Mifflin-St Jeor (1990) for BMR; standard activity multipliers;
~7700 kcal per kg of body mass for energy balance.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain import ActivityLevel, Goal, Sex

ACTIVITY_MULTIPLIERS: dict[ActivityLevel, float] = {
    ActivityLevel.sedentary: 1.2,
    ActivityLevel.light: 1.375,
    ActivityLevel.moderate: 1.55,
    ActivityLevel.active: 1.725,
    ActivityLevel.very_active: 1.9,
}

KCAL_PER_KG = 7700.0          # energy in ~1 kg of body mass
MAX_DEFICIT_PCT = 0.25        # never plan more than a 25% deficit below TDEE
MAX_SURPLUS_PCT = 0.20        # cap lean-bulk surplus
PROTEIN_G_PER_KG: dict[Goal, float] = {
    Goal.lose: 2.0,           # higher protein preserves muscle in a deficit
    Goal.maintain: 1.8,
    Goal.gain: 1.6,
}
FAT_PCT_OF_CALORIES = 0.25    # hormones / satiety floor


@dataclass(frozen=True)
class Macros:
    protein_g: int
    carbs_g: int
    fat_g: int

    def as_kcal(self) -> int:
        return self.protein_g * 4 + self.carbs_g * 4 + self.fat_g * 9


def bmr_mifflin(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    """Basal Metabolic Rate via Mifflin-St Jeor."""
    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        raise ValueError("weight, height and age must be positive")
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + (5 if sex == Sex.male else -161)


def tdee(bmr: float, activity_level: ActivityLevel) -> float:
    """Total Daily Energy Expenditure."""
    return bmr * ACTIVITY_MULTIPLIERS[activity_level]


def calorie_target(tdee_value: float, goal: Goal, rate_kg_per_week: float = 0.5) -> int:
    """Daily calorie target for a goal + desired rate of change.

    Applies a *relative* clamp (max 25% deficit / 20% surplus). Absolute safety
    floors (e.g. >=1200 kcal for women) are enforced separately by the Safety
    agent so this stays a pure energy-balance function.
    """
    rate = abs(rate_kg_per_week)
    daily_delta = (rate * KCAL_PER_KG) / 7.0

    if goal == Goal.lose:
        target = max(tdee_value - daily_delta, tdee_value * (1 - MAX_DEFICIT_PCT))
    elif goal == Goal.gain:
        target = min(tdee_value + daily_delta, tdee_value * (1 + MAX_SURPLUS_PCT))
    else:
        target = tdee_value
    return int(round(target))


def macros(calories: int, weight_kg: float, goal: Goal) -> Macros:
    """Split calories into protein/fat/carbs.

    Order of operations matters: protein is set by bodyweight first (muscle
    retention), fat gets a percentage floor, carbs fill the remainder.
    """
    protein_g = PROTEIN_G_PER_KG[goal] * weight_kg
    fat_g = (FAT_PCT_OF_CALORIES * calories) / 9.0
    remaining = calories - (protein_g * 4) - (fat_g * 9)
    carbs_g = max(remaining, 0) / 4.0
    return Macros(round(protein_g), round(carbs_g), round(fat_g))


def full_targets(
    sex: Sex,
    weight_kg: float,
    height_cm: float,
    age: int,
    activity_level: ActivityLevel,
    goal: Goal,
    rate_kg_per_week: float = 0.5,
) -> dict:
    """Convenience: profile -> {bmr, tdee, calories, macros}. Used by Nutrition agent."""
    b = bmr_mifflin(sex, weight_kg, height_cm, age)
    t = tdee(b, activity_level)
    cals = calorie_target(t, goal, rate_kg_per_week)
    m = macros(cals, weight_kg, goal)
    return {
        "bmr": round(b),
        "tdee": round(t),
        "calories": cals,
        "macros": {"protein_g": m.protein_g, "carbs_g": m.carbs_g, "fat_g": m.fat_g},
    }
