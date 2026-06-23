"""Profile document — the onboarding data every agent call reads.

1:1 with User (unique `user_id`). For V1 velocity it also carries the goal +
target rate (the data-model doc keeps a separate GOAL collection; we denormalize
here so a single profile read yields the complete input the agent graph needs —
documented trade-off, easy to split out later).
"""
from __future__ import annotations

from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel

from app.domain import ActivityLevel, Experience, Goal, Sex


class Profile(Document):
    user_id: PydanticObjectId
    name: str
    age: int
    sex: Sex
    height_cm: float
    weight_kg: float
    goal: Goal
    activity_level: ActivityLevel
    experience: Experience
    dietary_prefs: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    training_days: int = 3
    rate_kg_per_week: float = 0.5

    class Settings:
        name = "profiles"
        indexes = [IndexModel([("user_id", 1)], unique=True, name="uq_profile_user")]

    def to_agent_profile(self) -> dict[str, Any]:
        """The plain-dict shape the agent graph runner expects (enums -> str)."""
        return {
            "name": self.name,
            "age": self.age,
            "sex": self.sex.value,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "goal": self.goal.value,
            "activity_level": self.activity_level.value,
            "experience": self.experience.value,
            "dietary_prefs": list(self.dietary_prefs),
            "allergies": list(self.allergies),
            "equipment": list(self.equipment),
            "training_days": self.training_days,
            "rate_kg_per_week": self.rate_kg_per_week,
        }
