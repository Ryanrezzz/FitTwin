"""Progress Agent — fully deterministic analytics; LLM only prettifies the report."""
from __future__ import annotations

from app.agents.prompts import PROGRESS_SYSTEM
from app.agents.schemas import ProgressResult
from app.agents.state import trace
from app.agents.tools import progress_math as pm
from app.ai.llm import get_llm
from app.domain import Goal


def _label(slope_kg_wk: float, n_points: int) -> str:
    if n_points < 2:
        return "insufficient_data"
    if abs(slope_kg_wk) < 0.05:
        return "flat"
    return "losing" if slope_kg_wk < 0 else "gaining"


def progress_agent(state: dict) -> dict:
    p = state["profile"]
    history = state.get("history") or {}
    series = history.get("weight_series", [])
    logs = history.get("logs", [])
    plan = state.get("active_plan") or {}
    goal = Goal(p["goal"])

    trend = pm.weight_trend(series)
    adherence_pct = pm.adherence(logs, plan)
    plateau = pm.plateau_detected(trend, goal, adherence_pct)
    label = _label(trend.slope_kg_per_week, trend.n_points)

    highlights = [
        f"Weight trend: {label} ({trend.slope_kg_per_week:+.2f} kg/week).",
        f"Plan adherence: {adherence_pct}%.",
    ]
    if plateau:
        highlights.append("Plateau detected despite good adherence — time to adapt the plan.")
    elif label == "insufficient_data":
        highlights.append("Not enough data yet — keep logging for a clearer trend.")

    report_md = (
        "## Weekly Report\n"
        f"- **Trend:** {label} ({trend.slope_kg_per_week:+.2f} kg/wk)\n"
        f"- **Smoothed weight:** {trend.ewma_latest} kg\n"
        f"- **Adherence:** {adherence_pct}%\n"
        f"- **Plateau:** {'yes' if plateau else 'no'}\n"
    )
    # LLM only rewrites the prose; the numbers above are immutable
    report_md = get_llm().text(system=PROGRESS_SYSTEM, user=report_md, fallback=report_md)

    result = ProgressResult(
        trend=label,
        slope_kg_per_week=trend.slope_kg_per_week,
        plateau=plateau,
        adherence_pct=adherence_pct,
        highlights=highlights,
        report_md=report_md,
    )
    return {
        "progress_result": result.model_dump(),
        "steps": [
            trace(
                "progress",
                f"{label} {trend.slope_kg_per_week:+.2f}kg/wk, adh {adherence_pct}%, plateau={plateau}",
            )
        ],
    }
