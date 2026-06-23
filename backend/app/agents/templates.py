"""Deterministic meal & workout template builders.

These are the *fallback* (and offline) generators: the agent core produces a
complete, sensible plan with no LLM at all. When an LLM is configured it only
personalizes the language/selection on top of these.
"""
from __future__ import annotations

from app.domain import Experience

# ──────────────────────────────────────────────────────────────────────────
# MEALS
# ──────────────────────────────────────────────────────────────────────────
_MEAL_SPLIT = [("Breakfast", 0.28), ("Lunch", 0.34), ("Dinner", 0.30), ("Snack", 0.08)]

_PROTEIN_SOURCES = {
    "omnivore": ["chicken breast", "eggs", "greek yogurt", "lean beef", "fish", "whey shake"],
    "vegetarian": ["paneer", "eggs", "greek yogurt", "lentils (dal)", "tofu", "whey shake"],
    "vegan": ["tofu", "tempeh", "lentils (dal)", "chickpeas", "soy milk", "pea-protein shake"],
}
_CARB_SOURCES = ["rice", "oats", "whole-wheat roti", "potatoes", "banana", "quinoa"]
_VEG = ["mixed salad", "spinach", "broccoli", "seasonal vegetables"]


def _diet_key(dietary_prefs: list[str]) -> str:
    prefs = {p.lower() for p in dietary_prefs}
    if "vegan" in prefs:
        return "vegan"
    if "vegetarian" in prefs or "veg" in prefs:
        return "vegetarian"
    return "omnivore"


def build_meal_plan(
    calories: int, protein_g: int, dietary_prefs: list[str], allergies: list[str]
) -> list[dict]:
    diet = _diet_key(dietary_prefs)
    allergens = {a.lower() for a in allergies}
    proteins = [p for p in _PROTEIN_SOURCES[diet] if not any(a in p for a in allergens)]
    carbs = [c for c in _CARB_SOURCES if not any(a in c for a in allergens)]
    meals: list[dict] = []
    for i, (name, frac) in enumerate(_MEAL_SPLIT):
        p_src = proteins[i % len(proteins)] if proteins else "protein source"
        c_src = carbs[i % len(carbs)] if carbs else "complex carbs"
        items = [p_src, c_src]
        if name in ("Lunch", "Dinner"):
            items.append(_VEG[i % len(_VEG)])
        meals.append(
            {
                "name": name,
                "items": items,
                "kcal": round(calories * frac),
                "protein_g": round(protein_g * frac),
            }
        )
    return meals


# ──────────────────────────────────────────────────────────────────────────
# WORKOUTS
# ──────────────────────────────────────────────────────────────────────────
_HOME_SIGNALS = {"none", "no equipment", "bodyweight", "home", "bands", "resistance bands"}
_FREE_WEIGHTS = {"dumbbell", "dumbbells", "barbell", "gym", "kettlebell", "full gym", "machines"}

_GYM_POOL = {
    "full": ["Back Squat", "Bench Press", "Barbell Row", "Overhead Press"],
    "upper": ["Bench Press", "Barbell Row", "Overhead Press", "Lat Pulldown", "Biceps Curl"],
    "lower": ["Back Squat", "Romanian Deadlift", "Leg Press", "Calf Raise"],
    "push": ["Bench Press", "Overhead Press", "Incline DB Press", "Triceps Pushdown"],
    "pull": ["Deadlift", "Barbell Row", "Lat Pulldown", "Biceps Curl"],
    "legs": ["Back Squat", "Romanian Deadlift", "Leg Press", "Calf Raise"],
}
_HOME_POOL = {
    "full": ["Bodyweight Squat", "Push-ups", "Inverted/Band Rows", "Pike Push-ups"],
    "upper": ["Push-ups", "Band Rows", "Pike Push-ups", "Band Curls"],
    "lower": ["Bulgarian Split Squat", "Glute Bridge", "Reverse Lunge", "Calf Raise"],
    "push": ["Push-ups", "Pike Push-ups", "Chair Dips", "Band Press"],
    "pull": ["Inverted Rows", "Band Pulldown", "Band Row", "Towel Curl"],
    "legs": ["Bodyweight Squat", "Bulgarian Split Squat", "Glute Bridge", "Calf Raise"],
}

_REP_SCHEME = {
    Experience.beginner: (3, "8-12"),
    Experience.intermediate: (4, "6-10"),
    Experience.advanced: (4, "5-8"),
}


def is_home_setup(equipment: list[str]) -> bool:
    eq = {e.lower() for e in equipment}
    if eq & _FREE_WEIGHTS:
        return False
    if not eq or eq & _HOME_SIGNALS:
        return True
    return True  # default to the safer (no-equipment) assumption


def _split_for_days(days: int) -> tuple[str, list[str]]:
    if days <= 3:
        return "Full Body", ["full"] * max(days, 2)
    if days == 4:
        return "Upper / Lower", ["upper", "lower", "upper", "lower"]
    return "Push / Pull / Legs", (["push", "pull", "legs"] * 2)[:days]


def build_workout(experience: str, training_days: int, equipment: list[str]) -> dict:
    try:
        exp = Experience(experience)
    except ValueError:
        exp = Experience.beginner
    days = max(2, min(int(training_days or 3), 6))
    home = is_home_setup(equipment)
    pool = _HOME_POOL if home else _GYM_POOL
    sets, reps = _REP_SCHEME[exp]
    split_name, focuses = _split_for_days(days)

    load = (
        "Add reps or slow the tempo each week (progressive overload)."
        if home
        else "Add ~2.5 kg when you complete all sets at the top of the rep range."
    )
    sessions = []
    for i, focus in enumerate(focuses, start=1):
        exercises = [
            {"name": ex, "sets": sets, "reps": reps, "load_guidance": load}
            for ex in pool[focus][:4]
        ]
        sessions.append({"day": f"Day {i}", "focus": focus.capitalize(), "exercises": exercises})

    return {
        "split": f"{split_name} ({days} days/week, {'home' if home else 'gym'})",
        "sessions": sessions,
        "progression_notes": [load],
    }
