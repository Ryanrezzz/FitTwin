"""API request/response DTOs for the coach endpoints.

These are the HTTP contract — deliberately separate from the agent `schemas.py`
(LLM/graph I/O) and from any future DB models. Validation (bounds, enums) lives
here so the router rejects bad input *before* it reaches the agent graph.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.domain import ActivityLevel, Experience, Goal, Sex


class ProfileIn(BaseModel):
    """Onboarding profile — the single required input to drive the graph."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    age: int = Field(ge=13, le=100)
    sex: Sex
    height_cm: float = Field(gt=50, lt=260)
    weight_kg: float = Field(gt=20, lt=400)
    goal: Goal
    activity_level: ActivityLevel
    experience: Experience
    dietary_prefs: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    training_days: int = Field(default=3, ge=0, le=7)
    rate_kg_per_week: float = Field(default=0.5, ge=0.0, le=1.5)


class WeightEntry(BaseModel):
    """A single bodyweight measurement. `date` may be omitted for synthetic series."""

    model_config = ConfigDict(extra="forbid")

    date: date | None = None
    weight_kg: float = Field(gt=20, lt=400)


class LogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date | None = None
    calories: int | None = Field(default=None, ge=0, le=20000)
    protein_g: int | None = Field(default=None, ge=0, le=1000)
    steps: int | None = Field(default=None, ge=0, le=200000)
    workout_done: bool | None = None


class HistoryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weight_series: list[WeightEntry] = Field(default_factory=list)
    logs: list[LogEntry] = Field(default_factory=list)


class ActivePlanIn(BaseModel):
    """The user's current plan targets, used for adherence + adaptation."""

    model_config = ConfigDict(extra="forbid")

    calorie_target: int = Field(ge=0, le=20000)
    macros: dict[str, int] = Field(default_factory=dict)


class GeneratePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: ProfileIn


class WeeklyReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: ProfileIn
    history: HistoryIn = Field(default_factory=HistoryIn)
    active_plan: ActivePlanIn | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: ProfileIn
    message: str = Field(min_length=1, max_length=2000)
    history: HistoryIn = Field(default_factory=HistoryIn)
    active_plan: ActivePlanIn | None = None


class TraceStep(BaseModel):
    node: str
    summary: str


class CoachResponseOut(BaseModel):
    """Envelope returned by every coach endpoint: the composed response + trace."""

    final: dict
    steps: list[TraceStep]
