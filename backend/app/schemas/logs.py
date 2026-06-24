"""API DTOs for daily logging (the dashboard's quick-log controls)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DailyLogIn(BaseModel):
    """A partial update to today's log — only the provided fields are written."""

    model_config = ConfigDict(extra="forbid")

    water_ml: int | None = Field(default=None, ge=0, le=20000)
    steps: int | None = Field(default=None, ge=0, le=200000)
    calories: int | None = Field(default=None, ge=0, le=20000)
    protein_g: float | None = Field(default=None, ge=0, le=1000)
    workout_done: bool | None = None


class DailyLogOut(BaseModel):
    date: str
    water_ml: int = 0
    steps: int = 0
    calories: int = 0
    protein_g: float = 0
    workout_done: bool = False
