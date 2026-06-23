"""Service layer — use-cases that drive the agent graph.

The router knows HTTP; this service knows *use-cases* (generate a plan, run a
weekly review, answer a chat turn). It translates validated API DTOs into the
plain-dict shapes the graph runner expects and back, so the agent layer stays
ignorant of HTTP and Pydantic DTOs.

No persistence yet — the graph is stateless given a profile + history, so these
endpoints are pure functions of their input. DB-backed variants (load profile by
user, persist versioned plan) layer on top of this same seam in a later sprint.
"""
from __future__ import annotations

from typing import Any

from app.agents.runner import run_coach
from app.config import settings
from app.schemas.coach import ActivePlanIn, ChatRequest, HistoryIn, WeeklyReviewRequest


def _history_to_runner(history: HistoryIn) -> dict[str, Any]:
    """DTO -> the {weight_series: [(key, kg)], logs: [{...}]} shape the tools expect.

    `date` is preserved when present (regression keys on it); otherwise the entry
    index is used as the day offset, which the progress math accepts as an int key.
    """
    weight_series = [
        (w.date if w.date is not None else i, w.weight_kg)
        for i, w in enumerate(history.weight_series)
    ]
    logs = [log.model_dump(exclude_none=True) for log in history.logs]
    return {"weight_series": weight_series, "logs": logs}


def _plan_to_runner(plan: ActivePlanIn | None) -> dict[str, Any] | None:
    return plan.model_dump() if plan is not None else None


class CoachService:
    """Drives the compiled LangGraph for each coach use-case."""

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        result = run_coach(
            graph=self._graph,
            recursion_limit=settings.agent_recursion_limit,
            **kwargs,
        )
        return {"final": result["final"], "steps": result["steps"]}

    def generate_plan(self, *, profile: dict[str, Any], user_id: str) -> dict[str, Any]:
        return self._run(profile=profile, trigger="generate_plan", user_id=user_id)

    def weekly_review(
        self, req: WeeklyReviewRequest, *, profile: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        return self._run(
            profile=profile,
            history=_history_to_runner(req.history),
            active_plan=_plan_to_runner(req.active_plan),
            trigger="weekly_review",
            user_id=user_id,
        )

    def chat(
        self, req: ChatRequest, *, profile: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        return self._run(
            profile=profile,
            message=req.message,
            history=_history_to_runner(req.history),
            active_plan=_plan_to_runner(req.active_plan),
            trigger="chat",
            user_id=user_id,
        )
