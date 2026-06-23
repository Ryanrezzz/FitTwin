"""Service layer — use-cases that drive the agent graph and persist results.

The router knows HTTP; this service knows *use-cases* (generate a plan, run a
weekly review, answer a chat turn). It translates validated API DTOs into the
plain-dict shapes the graph runner expects, runs the (synchronous) graph off the
event loop, and persists any complete plan the run produces as a new version.

History still arrives in the request body until daily logs are persisted; the
active plan and profile are loaded from the DB by the router and passed in.
"""
from __future__ import annotations

import functools
from typing import Any

import anyio

from app.agents.runner import run_coach
from app.config import settings
from app.repositories.plan_repo import PlanRepo
from app.schemas.coach import ChatRequest, HistoryIn, WeeklyReviewRequest


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


class CoachService:
    """Drives the compiled LangGraph for each coach use-case and persists plans."""

    def __init__(self, graph: Any, plans: PlanRepo) -> None:
        self._graph = graph
        self._plans = plans

    async def _run(self, **kwargs: Any) -> dict[str, Any]:
        # graph.invoke is synchronous (and may call out to an LLM) — keep it off
        # the event loop so the API stays responsive.
        call = functools.partial(
            run_coach, graph=self._graph, recursion_limit=settings.agent_recursion_limit, **kwargs
        )
        result = await anyio.to_thread.run_sync(call)
        out: dict[str, Any] = {"final": result["final"], "steps": result["steps"]}
        await self._persist_if_complete(out, user_id=kwargs["user_id"])
        return out

    async def _persist_if_complete(self, out: dict[str, Any], *, user_id: str) -> None:
        """A run that yields both nutrition and workout is a full plan -> version it."""
        final = out["final"]
        nutrition, workout = final.get("nutrition"), final.get("workout")
        if nutrition and workout:
            plan = await self._plans.create_version(
                user_id, nutrition=nutrition, workout=workout, intent=final.get("intent")
            )
            out["plan_id"] = str(plan.id)
            out["plan_version"] = plan.version

    async def generate_plan(self, *, profile: dict[str, Any], user_id: str) -> dict[str, Any]:
        return await self._run(profile=profile, trigger="generate_plan", user_id=user_id)

    async def weekly_review(
        self, req: WeeklyReviewRequest, *, profile: dict[str, Any],
        active_plan: dict[str, Any] | None, user_id: str,
    ) -> dict[str, Any]:
        return await self._run(
            profile=profile,
            history=_history_to_runner(req.history),
            active_plan=active_plan,
            trigger="weekly_review",
            user_id=user_id,
        )

    async def chat(
        self, req: ChatRequest, *, profile: dict[str, Any],
        active_plan: dict[str, Any] | None, user_id: str,
    ) -> dict[str, Any]:
        return await self._run(
            profile=profile,
            message=req.message,
            history=_history_to_runner(req.history),
            active_plan=active_plan,
            trigger="chat",
            user_id=user_id,
        )
