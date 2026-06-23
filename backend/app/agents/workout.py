"""Workout Agent — deterministic split/template, LLM personalizes within equipment."""
from __future__ import annotations

from app.agents import templates
from app.agents.prompts import WORKOUT_SYSTEM
from app.agents.schemas import Session, WorkoutResult
from app.agents.state import trace
from app.ai.llm import get_llm


def workout_agent(state: dict) -> dict:
    p = state["profile"]
    wk = templates.build_workout(
        p.get("experience", "beginner"), p.get("training_days", 3), p.get("equipment", [])
    )

    notes = list(wk["progression_notes"])
    progress = state.get("progress_result")
    if progress and progress.get("plateau"):
        notes.append(
            "Plateau: add one set to the main lifts and add 2×20 min Zone-2 cardio this week."
        )

    fallback = WorkoutResult(
        split=wk["split"],
        sessions=[Session(**s) for s in wk["sessions"]],
        progression_notes=notes,
    )

    user = (
        f"Experience: {p.get('experience')}, {p.get('training_days')} days/week, "
        f"equipment: {p.get('equipment') or 'none (bodyweight)'}. "
        f"Personalize exercise selection ONLY within available equipment."
    )
    result = get_llm().structured(
        system=WORKOUT_SYSTEM, user=user, schema=WorkoutResult, fallback=fallback
    )
    if not result.progression_notes:
        result.progression_notes = notes

    return {
        "workout_result": result.model_dump(),
        "steps": [trace("workout", result.split)],
    }
