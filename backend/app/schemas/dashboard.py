"""API DTOs for the dashboard endpoints (HTTP contract, derived on read)."""
from __future__ import annotations

from pydantic import BaseModel


class AgentInfo(BaseModel):
    key: str
    name: str
    mode: str          # rule | llm | hybrid
    blurb: str


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

    # how the coach thinks today (see app/agents/registry.py)
    engine: str                 # rule | gemini | openai | local
    agents: list[AgentInfo]
