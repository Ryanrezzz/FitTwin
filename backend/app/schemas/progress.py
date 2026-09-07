"""Bodyweight tracking DTOs."""
from __future__ import annotations

from datetime import date as DateType

from pydantic import BaseModel, ConfigDict, Field


class WeightIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Bounds are a data-quality guard, not a medical judgement: they reject
    # typos like 750 kg or 7.5 kg that would otherwise poison the trend line.
    weight_kg: float = Field(gt=20, lt=400)
    date: DateType | None = None
    note: str = Field(default="", max_length=200)


class WeightOut(BaseModel):
    date: str
    weight_kg: float
    note: str = ""


class WeightSeriesOut(BaseModel):
    entries: list[WeightOut] = []
    latest_kg: float | None = None
    change_kg: float | None = None
    days_tracked: int = 0
