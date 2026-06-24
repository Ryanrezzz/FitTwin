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


class GymType(str, Enum):
    """Where/how the user trains — seeds the effective equipment set."""

    full_gym = "full_gym"        # commercial gym: assume all machines + free weights
    home_gym = "home_gym"        # a stocked home setup (uses the checked equipment)
    partial = "partial"          # a few items (dumbbells/bands/etc.)
    bodyweight = "bodyweight"    # no equipment


# Effective equipment unlocked by gym type (free-weight tokens flip the workout
# template from the home pool to the gym pool — see agents/templates.py).
FULL_GYM_EQUIPMENT = [
    "barbell", "dumbbells", "cable_machine", "leg_press_machine",
    "bench", "pull_up_bar", "treadmill", "machines",
]
