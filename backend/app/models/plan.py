"""Plan document — a versioned, self-contained snapshot of the coach's output.

A plan is read as one unit, so the nutrition + workout structures are embedded
(see docs/03-data-model.md). New week / re-plan = a new `version`; the old one is
kept (audit + "what changed") with `active` flipped off. `{user_id, version}` is
unique; `{user_id, active}` serves "get my current plan".
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Plan(Document):
    user_id: PydanticObjectId
    version: int
    active: bool = True
    intent: str | None = None            # what produced it (generate_plan / weekly_review …)
    calorie_target: int
    macros: dict[str, int] = Field(default_factory=dict)
    nutrition: dict[str, Any] = Field(default_factory=dict)   # full NutritionResult
    workout: dict[str, Any] = Field(default_factory=dict)     # full WorkoutResult
    degraded: bool = False               # generated via fallback (LLM down)
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "plans"
        indexes = [
            IndexModel([("user_id", 1), ("version", 1)], unique=True, name="uq_plan_version"),
            IndexModel([("user_id", 1), ("active", 1)], name="ix_plan_active"),
        ]
