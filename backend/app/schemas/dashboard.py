"""API DTOs for the dashboard endpoints (HTTP contract, derived on read)."""
from __future__ import annotations

from pydantic import BaseModel


class AgentInfo(BaseModel):
    key: str
    name: str
    mode: str          # rule | llm | hybrid
    blurb: str


class MealOut(BaseModel):
    """A meal on the dashboard. `slot` and `dish_id` are what the UI needs to
    offer a Rotate button and label what it swapped."""

    name: str
    items: list[str]
    kcal: int
    protein_g: int
    slot: str = ""
    dish: str = ""
    dish_id: str = ""
    carbs_g: int = 0
    fat_g: int = 0


class DashboardSummaryOut(BaseModel):
    """The overview-card values + the hybrid coaching-engine map."""

    goal: str
    current_weight_kg: float
    target_weight_kg: float
    est_goal_weeks: int | None = None

    calorie_target: int
    calories_remaining: int
    protein_target_g: int
    protein_remaining_g: int

    water_goal_ml: int
    water_ml: int
    step_goal: int
    steps: int

    workout_target_days: int
    workouts_done: int
    workout_completion_pct: int
    streak_days: int

    # today's meal suggestion (rotates daily so it isn't the same every day)
    today_meals: list[MealOut] = []

    # how the coach thinks today (see app/agents/registry.py)
    engine: str                 # rule | gemini | openai | local
    agents: list[AgentInfo]
