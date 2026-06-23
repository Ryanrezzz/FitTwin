"""Pydantic I/O contracts for the agents.

These are also the schemas the LLM is asked to fill via `with_structured_output`,
so the service layer always receives validated objects, never free text.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class MacrosOut(BaseModel):
    protein_g: int
    carbs_g: int
    fat_g: int


class Meal(BaseModel):
    name: str                       # "Breakfast"
    items: list[str]
    kcal: int
    protein_g: int


class NutritionResult(BaseModel):
    calories: int
    macros: MacrosOut
    meal_plan: list[Meal] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    rationale: str = ""


class Exercise(BaseModel):
    name: str
    sets: int
    reps: str                       # "8-12"
    load_guidance: str = ""


class Session(BaseModel):
    day: str
    focus: str
    exercises: list[Exercise]


class WorkoutResult(BaseModel):
    split: str
    sessions: list[Session] = Field(default_factory=list)
    progression_notes: list[str] = Field(default_factory=list)


class ProgressResult(BaseModel):
    trend: str                      # "losing" | "gaining" | "flat" | "insufficient_data"
    slope_kg_per_week: float
    plateau: bool
    adherence_pct: float
    highlights: list[str] = Field(default_factory=list)
    report_md: str = ""


class MotivationResult(BaseModel):
    message: str
    streak_days: int = 0
    nudge: str = ""
    tone: str = "supportive"


class SafetyVerdict(BaseModel):
    approved: bool = True
    clamps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_disclaimer: bool = False


class CoachResponse(BaseModel):
    """Final composed payload returned to the caller / streamed to the UI."""

    message: str
    intent: str
    agents_used: list[str] = Field(default_factory=list)
    nutrition: NutritionResult | None = None
    workout: WorkoutResult | None = None
    progress: ProgressResult | None = None
    motivation: MotivationResult | None = None
    safety: SafetyVerdict | None = None
