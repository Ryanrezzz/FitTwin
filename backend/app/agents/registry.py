"""Single source of truth for the hybrid agent classification.

Each agent is one of three execution modes (see docs/02-multi-agent-system.md §0):
  - "rule"   : pure deterministic Python, no model call.
  - "llm"    : the LLM does the language/synthesis (grounded in tool numbers).
  - "hybrid" : deterministic core + optional LLM personalization on top.

This is imported by the dashboard so the UI can *show* how the coach thinks, and
it documents the decision in code rather than only in prose.
"""
from __future__ import annotations

# Ordered for display. `key` matches the graph node names where one exists.
AGENTS: list[dict[str, str]] = [
    {"key": "progress", "name": "Progress", "mode": "rule",
     "blurb": "Trend, plateau & adherence — reproducible math, no model."},
    {"key": "safety", "name": "Safety", "mode": "rule",
     "blurb": "Hard guardrails clamp unsafe plans. A limit can't be a guess."},
    {"key": "nutrition", "name": "Nutrition", "mode": "llm",
     "blurb": "Targets from tools; the model assembles meals around them."},
    {"key": "motivation", "name": "Motivation", "mode": "llm",
     "blurb": "Language work, grounded in your real streak/adherence."},
    {"key": "coach", "name": "AI Coach Chat", "mode": "llm",
     "blurb": "Conversational synthesis over the specialists' outputs."},
    {"key": "workout", "name": "Workout", "mode": "hybrid",
     "blurb": "Rule-picked split & equipment; LLM personalizes exercises."},
]

AGENT_MODE: dict[str, str] = {a["key"]: a["mode"] for a in AGENTS}
