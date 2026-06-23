"""Motivation Agent — language work, grounded in real streak/adherence numbers."""
from __future__ import annotations

from app.agents.prompts import MOTIVATION_SYSTEM
from app.agents.schemas import MotivationResult
from app.agents.state import trace
from app.ai.llm import get_llm


def _streak_days(logs: list[dict]) -> int:
    """Trailing consecutive days that were logged or had a workout."""
    streak = 0
    for log in reversed(logs):
        if log.get("workout_done") or log.get("calories", 0) > 0:
            streak += 1
        else:
            break
    return streak


def motivation_agent(state: dict) -> dict:
    history = state.get("history") or {}
    logs = history.get("logs", [])
    streak = _streak_days(logs)
    progress = state.get("progress_result") or {}
    adherence_pct = progress.get("adherence_pct", 0)

    base = (
        f"You're on a {streak}-day streak"
        + (f" at {adherence_pct}% adherence" if adherence_pct else "")
        + " — consistency is what moves the needle. Keep stacking wins."
    )
    nudge = "Log today to extend your streak." if streak else "Log your first day to wake up your Twin."

    message = get_llm().text(system=MOTIVATION_SYSTEM, user=base, fallback=base)
    result = MotivationResult(message=message, streak_days=streak, nudge=nudge, tone="supportive")

    return {
        "motivation_result": result.model_dump(),
        "steps": [trace("motivation", f"streak {streak}d")],
    }
