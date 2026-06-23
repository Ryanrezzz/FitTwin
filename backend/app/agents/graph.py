"""LangGraph wiring.

    START → route → ┌─ progress ─(plateau?)─→ [nutrition, workout] ─┐
                    ├─ nutrition ──────────────────────────────────┤
                    ├─ workout ────────────────────────────────────┤→ safety → compose → END
                    ├─ motivation ─────────────────────────────────┤
                    └─ safety (direct) ────────────────────────────┘

Safety is unconditional: every plan-producing path flows through it before compose.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.motivation import motivation_agent
from app.agents.nutrition import nutrition_agent
from app.agents.orchestrator import (
    after_progress,
    compose_final,
    orchestrator_route,
    route_selector,
)
from app.agents.progress import progress_agent
from app.agents.safety import safety_agent
from app.agents.state import AgentState
from app.agents.workout import workout_agent


def build_graph():
    b = StateGraph(AgentState)

    b.add_node("route", orchestrator_route)
    b.add_node("progress", progress_agent)
    b.add_node("nutrition", nutrition_agent)
    b.add_node("workout", workout_agent)
    b.add_node("motivation", motivation_agent)
    b.add_node("safety", safety_agent)
    b.add_node("compose", compose_final)

    b.add_edge(START, "route")
    b.add_conditional_edges(
        "route", route_selector,
        ["progress", "nutrition", "workout", "motivation", "safety"],
    )
    b.add_conditional_edges(
        "progress", after_progress,
        ["nutrition", "workout", "motivation"],
    )
    b.add_edge("nutrition", "safety")
    b.add_edge("workout", "safety")
    b.add_edge("motivation", "safety")
    b.add_edge("safety", "compose")
    b.add_edge("compose", END)

    return b.compile()
