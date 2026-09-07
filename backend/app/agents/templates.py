"""Deterministic meal & workout template builders.

These are the *fallback* (and offline) generators: the agent core produces a
complete, sensible plan with no LLM at all. When an LLM is configured it only
personalizes the language/selection on top of these.
"""
from __future__ import annotations

from app.agents.tools import meal_builder
from app.domain import Experience

# ──────────────────────────────────────────────────────────────────────────
# MEALS — delegated to the catalog-backed builder.
#
# This used to invent numbers: `kcal = daily_target * meal_fraction`, printed
# beside a dish name nothing had measured. Two different diets produced
# identical calories, which is the tell. Meals are now composed from
# `data/foods_in.py` recipes and the kcal/protein are SUMMED from the portions
# actually listed — see tools/meal_builder.py.
# ──────────────────────────────────────────────────────────────────────────


def build_meal_plan(
    calories: int,
    protein_g: int,
    dietary_prefs: list[str],
    allergies: list[str],
    day_offset: int = 0,
    age: int = 30,
    choices: dict[str, str] | None = None,
    rotations: dict[str, int] | None = None,
) -> list[dict]:
    """One day's meals with macros computed from the food on the plate."""
    return meal_builder.build_day(
        calories=calories,
        protein_g=protein_g,
        dietary_prefs=dietary_prefs,
        allergies=allergies,
        age=age,
        day_offset=day_offset,
        choices=choices,
        rotations=rotations,
    )


# ──────────────────────────────────────────────────────────────────────────
# WORKOUTS — split & exercise selection adapt to EQUIPMENT, EXPERIENCE *and AGE*.
# A 22-year-old trains explosively near their limit; a 55-year-old gets
# joint-friendly variations, higher reps and more warm-up. Same math, different
# movement selection and intensity.
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

# 50+ : swap heavy axial-loaded / higher-impact lifts for joint-friendly variants.
_MASTERS_SWAPS = {
    "Back Squat": "Goblet Squat",
    "Deadlift": "Romanian Deadlift",
    "Bench Press": "DB Bench Press",
    "Overhead Press": "Seated DB Shoulder Press",
    "Barbell Row": "Chest-Supported DB Row",
    "Bulgarian Split Squat": "Reverse Lunge",
    "Pike Push-ups": "Incline Push-ups",
    "Chair Dips": "Bench Dips (feet supported)",
}
# 50+ : moderate the rep range to protect joints (lighter, more reps).
_MASTERS_REPS = {"5-8": "8-12", "6-10": "8-12", "8-12": "10-15"}

# Under-30 : append one explosive/athletic finisher per focus (no equipment
# needed, so it works home or gym) — the "more athletic" training the young
# user expects and an older user shouldn't be doing.
_YOUNG_FINISHER = {
    "full": "Jump Squats",
    "lower": "Jump Squats",
    "legs": "Box Jumps",
    "push": "Plyo Push-ups",
    "upper": "Plyo Push-ups",
    "pull": "Burpees",
}

_AGE_NOTES = {
    "young": "You recover fast — train close to your limit and add load weekly; "
             "the explosive finisher builds power and athleticism.",
    "adult": "Balance intensity with recovery — keep 1–2 reps in reserve on your last set.",
    "masters": "Joint-friendly variations selected. Warm up 8–10 min, prioritise form over load, "
               "and leave an extra rest day between hard sessions.",
}


def is_home_setup(equipment: list[str]) -> bool:
    eq = {e.lower() for e in equipment}
    if eq & _FREE_WEIGHTS:
        return False
    if not eq or eq & _HOME_SIGNALS:
        return True
    return True  # default to the safer (no-equipment) assumption


def _age_band(age: int) -> str:
    if age < 30:
        return "young"
    if age < 50:
        return "adult"
    return "masters"


def _split_for_days(days: int) -> tuple[str, list[str]]:
    if days <= 3:
        return "Full Body", ["full"] * max(days, 2)
    if days == 4:
        return "Upper / Lower", ["upper", "lower", "upper", "lower"]
    return "Push / Pull / Legs", (["push", "pull", "legs"] * 2)[:days]


def build_workout(
    experience: str, training_days: int, equipment: list[str], age: int = 30
) -> dict:
    try:
        exp = Experience(experience)
    except ValueError:
        exp = Experience.beginner
    days = max(2, min(int(training_days or 3), 6))
    home = is_home_setup(equipment)
    pool = _HOME_POOL if home else _GYM_POOL
    band = _age_band(int(age or 30))
    sets, reps = _REP_SCHEME[exp]
    if band == "masters":
        sets, reps = max(2, sets - 1), _MASTERS_REPS.get(reps, reps)
    split_name, focuses = _split_for_days(days)

    load = (
        "Add reps or slow the tempo each week (progressive overload)."
        if home
        else "Add ~2.5 kg when you complete all sets at the top of the rep range."
    )
    sessions = []
    for i, focus in enumerate(focuses, start=1):
        exercises = []
        for ex in pool[focus][:4]:
            if band == "masters":
                ex = _MASTERS_SWAPS.get(ex, ex)
            exercises.append({"name": ex, "sets": sets, "reps": reps, "load_guidance": load})
        if band == "young" and focus in _YOUNG_FINISHER:
            exercises.append(
                {
                    "name": _YOUNG_FINISHER[focus],
                    "sets": 3,
                    "reps": "6-8 explosive",
                    "load_guidance": "Move fast and powerfully; full recovery between sets.",
                }
            )
        sessions.append({"day": f"Day {i}", "focus": focus.capitalize(), "exercises": exercises})

    return {
        "split": f"{split_name} ({days} days/week, {'home' if home else 'gym'}, age {age})",
        "sessions": sessions,
        "progression_notes": [load, _AGE_NOTES[band]],
    }
