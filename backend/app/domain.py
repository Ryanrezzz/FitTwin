"""Shared domain enums used across tools and agents.

Kept dependency-free (stdlib only) so the deterministic tools can be imported
and unit-tested without pydantic, langgraph, or any LLM SDK installed.
"""
from __future__ import annotations

from enum import Enum


class Sex(str, Enum):
    male = "male"
    female = "female"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"       # little/no exercise
    light = "light"               # 1-3 days/week
    moderate = "moderate"         # 3-5 days/week
    active = "active"             # 6-7 days/week
    very_active = "very_active"   # hard daily training / physical job


class Goal(str, Enum):
    lose = "lose"
    maintain = "maintain"
    gain = "gain"


class Experience(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
