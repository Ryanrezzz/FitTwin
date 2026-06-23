"""The shared LangGraph state.

Every node returns a *partial* update which LangGraph merges. `steps` uses an
append reducer so each node leaves a trace entry -> this becomes the persisted
AgentRun (observability / reproducibility).
"""
from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    # ── inputs (set once when the run starts) ──
    user_id: str
    trigger: str                 # "chat" | "generate_plan" | "weekly_review"
    message: str | None
    profile: dict[str, Any]
    history: dict[str, Any]
    active_plan: dict[str, Any] | None

    # ── routing ──
    intent: str | None
    route: list[str]

    # ── specialist outputs (each writes its own slice) ──
    progress_result: dict[str, Any] | None
    nutrition_result: dict[str, Any] | None
    workout_result: dict[str, Any] | None
    motivation_result: dict[str, Any] | None
    safety_verdict: dict[str, Any] | None

    # ── bookkeeping ──
    steps: Annotated[list[dict[str, Any]], add]
    final: dict[str, Any] | None


def trace(node: str, summary: str, **extra: Any) -> dict[str, Any]:
    """Build a single trace entry for the `steps` log."""
    entry = {"node": node, "summary": summary}
    if extra:
        entry.update(extra)
    return entry
