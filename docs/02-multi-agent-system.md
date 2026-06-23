# 02 · Multi-Agent System

The heart of FitTwin. Six agents collaborate over a **single typed LangGraph state object**. The Orchestrator
routes; specialists produce structured proposals; the Safety agent gates; a reducer composes the final answer.

> Design principle: **agents own judgment, tools own arithmetic.** Every number a user could act on
> (calories, macros, plateau verdict) comes from a deterministic Python tool. The LLM decides *what to do* and
> *how to say it*, not *what 1.55 × BMR equals*.

---

## 1. The shared graph state

```python
# app/agents/state.py
from typing import Literal, TypedDict, Annotated
from operator import add

class AgentState(TypedDict):
    # inputs (immutable within a run)
    user_id: str
    message: str | None                 # present for chat; None for scheduled review
    profile: dict                       # snapshot: age, sex, height, weight, goal, activity, diet, equipment, experience
    history: dict                       # aggregated logs: weight series, avg cals/protein, steps, adherence%
    active_plan: dict | None

    # routing
    intent: str | None
    route: list[str]                    # which specialists to run

    # specialist outputs (each writes its own slice)
    progress_result: dict | None
    nutrition_result: dict | None
    workout_result: dict | None
    motivation_result: dict | None

    # safety
    safety_verdict: dict | None         # {approved: bool, clamps: [...], warnings: [...]}

    # bookkeeping (append-only via reducer)
    steps: Annotated[list[dict], add]   # trace of node executions for AgentRun
    final: dict | None                  # composed response returned to user
```

Each node returns a **partial** state update; LangGraph merges it. `steps` uses an `add` reducer so every node
appends a trace entry — that becomes the persisted `AgentRun` (see [`03-data-model.md`](03-data-model.md)).

---

## 2. The graph

```mermaid
flowchart TD
    START((start)) --> ROUTE[Orchestrator: route]
    ROUTE -->|needs progress| PROG[Progress Agent]
    ROUTE -->|nutrition only| NUTR[Nutrition Agent]
    ROUTE -->|workout only| WORK[Workout Agent]
    ROUTE -->|chit-chat/motivation| MOT[Motivation Agent]

    PROG --> DECIDE{plateau / off-track?}
    DECIDE -->|yes| NUTR
    DECIDE -->|yes| WORK
    DECIDE -->|on track| MOT

    NUTR --> SAFE
    WORK --> SAFE
    MOT --> SAFE
    PROG -.->|info-only query| SAFE

    SAFE[🛡️ Safety Agent gate] -->|approved| COMPOSE[Reducer: compose final]
    SAFE -->|clamp + annotate| COMPOSE
    COMPOSE --> END((end))
```

- **Conditional edges** out of `ROUTE` and `DECIDE` are functions over state (LangGraph `add_conditional_edges`),
  not LLM calls — fast and testable. The *intent classification* that fills `route` is one cheap LLM call (or a
  rules+LLM hybrid).
- **Safety is unconditional.** Every path that mutates a plan flows through `SAFE` before `COMPOSE`. You cannot
  produce a user-facing plan that skipped the gate.
- **Recursion limit + step budget + timeout** are set on the compiled graph to bound cost.

```python
graph = StateGraph(AgentState)
graph.add_node("route", orchestrator_route)
graph.add_node("progress", progress_agent)
graph.add_node("nutrition", nutrition_agent)
graph.add_node("workout", workout_agent)
graph.add_node("motivation", motivation_agent)
graph.add_node("safety", safety_agent)
graph.add_node("compose", compose_final)
graph.set_entry_point("route")
graph.add_conditional_edges("route", pick_specialists)      # -> subset of nodes
graph.add_conditional_edges("progress", after_progress)     # plateau? -> nutrition+workout | motivation
# nutrition/workout/motivation -> safety ; safety -> compose ; compose -> END
app_graph = graph.compile(checkpointer=mongo_saver)         # resumable runs
```

---

## 3. The six agents

### 3.1 Orchestrator Agent
**Job:** receive query → classify intent → choose agents → maintain workflow state → compose output.
**Inputs:** message (or scheduled trigger), profile, history.
**Outputs:** `route`, then the merged `final` response.
**How:** one structured LLM call returns `{intent, route[], rationale}`; deterministic edges do the rest. It does
*not* generate plan content — it delegates. This separation keeps each specialist independently testable.

### 3.2 Nutrition Agent
**Job:** BMR → TDEE → calorie target → macros → meal plan → adapt.
**Inputs:** profile, `progress_result`.
**Outputs:** `{calories, protein_g, carbs_g, fat_g, meal_plan[], changes[]}`.
**Tools (deterministic):**
```python
def bmr_mifflin(sex, weight_kg, height_cm, age) -> float        # Mifflin–St Jeor
def tdee(bmr, activity_level) -> float                          # ×1.2 … ×1.9
def calorie_target(tdee, goal, rate_kg_per_week) -> int         # deficit/surplus, clamped
def macros(calories, weight_kg, goal) -> Macros                 # protein 1.6–2.2 g/kg first, then fat 25%, rest carbs
```
The **LLM only builds the meal plan** (food choices honoring diet prefs/allergies) around tool-computed targets,
and writes the human explanation. *Why:* a wrong macro number is a real-world harm; a slightly odd meal swap is not.

### 3.3 Workout Agent
**Job:** generate weekly program; progressive overload; intensity adjustment; home vs gym.
**Inputs:** profile (experience, equipment, days/week), `progress_result`.
**Outputs:** `{split, sessions[{day, exercises[{name, sets, reps, load_guidance}]}], progression_notes}`.
**Logic:** template skeleton selected deterministically from `(experience, days, equipment)` → LLM personalizes
exercise selection within the equipment constraint (e.g. "no dumbbells" ⇒ bodyweight/band substitutions) and
applies progressive-overload rules (add reps→add sets→add load) based on adherence from `progress_result`.

### 3.4 Progress Agent
**Job:** track weight/calories/protein/steps/adherence; detect plateau vs improvement; weekly report.
**Inputs:** aggregated `history`.
**Outputs:** `{trend, slope_kg_per_week, plateau: bool, adherence_pct, highlights[], report_md}`.
**Tools (deterministic, the brain of adaptation):**
```python
def weight_trend(series) -> Trend            # linear regression slope + EWMA to kill daily water noise
def plateau_detected(trend, goal, weeks=2) -> bool   # |slope| < threshold while adherence high
def adherence(logs, plan) -> float           # % days logged within target bands
```
**Why tools:** plateau detection must be *explainable and consistent* ("0.05 kg/wk over 14 days while 92%
adherent"), never a vibe from the model.

### 3.5 Motivation Agent
**Job:** daily check-ins, motivational messages, goal reminders, habit streaks.
**Inputs:** adherence, streaks, recent wins.
**Outputs:** `{message, streak_days, nudge, tone}`.
This is the one agent that is *mostly* LLM language work — grounded in real streak/adherence numbers so it's
specific ("12-day protein streak — one more for a personal best") not generic hype.

### 3.6 Safety Agent (the gate)
**Job:** prevent unhealthy deficits, unrealistic goals, overtraining, dangerous advice.
**Inputs:** proposed plan, profile, history.
**Outputs:** `{approved, clamps[], warnings[], requires_disclaimer}`.
**Rules (deterministic guardrails, LLM only for phrasing the warning):**
```python
MIN_CALORIES = {"female": 1200, "male": 1500}      # hard floor
MAX_DEFICIT_PCT = 0.25                              # ≤25% below TDEE
MAX_RATE_KG_WK = 0.01 * weight_kg                   # ~1%/wk loss cap
MAX_TRAINING_DAYS = 6                               # overtraining guard
```
If a proposed calorie target violates a floor, Safety **clamps** it (raises to the floor), annotates the reason,
and the clamped value is what gets stored/shown. Unrealistic goals ("lose 10 kg in 2 weeks") trigger a reframe +
disclaimer. **Medical red flags** (eating-disorder language, injury/pain, pregnancy) short-circuit to a
"please consult a professional" response. This agent is why the product can claim to be safe.

---

## 4. Intent → routing table

| User says | Intent | Route | Notable behavior |
|---|---|---|---|
| "I haven't lost weight this week" | `progress_concern` | Progress → (plateau) → Nutrition + Workout → Safety | Adaptation loop |
| "I gained 1 kg this week" | `progress_concern` | Progress → Nutrition (check noise vs trend) → Safety | EWMA avoids overreacting to water |
| "I ate 250g chicken and rice today" | `log_food` | (tool) parse + log → Nutrition (remaining macros) | Writes a `daily_log`, no full re-plan |
| "Create a vegetarian meal plan" | `nutrition_request` | Nutrition → Safety | Respects diet pref, keeps targets |
| "I have no dumbbells" | `equipment_change` | Workout (substitute) → Safety | Updates equipment in profile + re-plans workout |
| "Give me a pep talk" | `motivation` | Motivation | Grounded in streaks |
| "Is 1000 calories ok?" | `safety_question` | Safety (direct) | Educational + floor warning |

The food-logging path shows an important nuance: **not every message is a re-plan.** Logging is a cheap write +
a quick "you have X kcal / Y g protein left today" — the orchestrator distinguishes *log* from *advise*.

---

## 5. Collaboration example (full trace)

**User:** "I haven't lost weight this week."

```
route        → intent=progress_concern, route=[progress]
progress     → slope=-0.02 kg/wk (14d), adherence=92% ⇒ plateau=true
after_progress → plateau ⇒ go to nutrition + workout
nutrition    → TDEE recheck (weight ↓ since start ⇒ TDEE ↓) → deficit +100 kcal, hold protein 2.0 g/kg
workout      → add 1 progressive-overload set to compounds + 2×20min Zone-2 cardio
safety       → new target 1,780 kcal > floor 1,500 & deficit 18% < 25% ⇒ approved
compose      → coach message + updated targets card + new workout + weekly report
persist      → version plan v4, store WeeklyReport + AgentRun(steps[])
```

This is the literal flow from the spec (Progress → plateau → Nutrition → Workout → Safety → final), expressed as
graph edges so it's testable end-to-end with fixture data and **no LLM** (tools-only) in unit tests.

---

## 6. Prompting & reliability conventions

- **Structured outputs everywhere.** Each agent uses `with_structured_output(PydanticModel)` so the service layer
  receives validated objects, not free text. One self-heal retry on validation failure, then fall back to the
  deterministic tool result.
- **System prompts are versioned** in `app/agents/prompts/` and hashed into the `AgentRun` trace for reproducibility.
- **Token/cost budget** per run is enforced; specialists get only the state slice they need (not the whole history).
- **Every run is traced to LangSmith** (project tagged by env) — you can replay a user's exact weekly review.
- **Determinism for tests:** `temperature=0` in CI, and a `FakeLLM` provider returns canned structured outputs so
  the whole graph is unit-testable offline.

---

## 7. LLM provider abstraction

```python
# app/ai/llm.py
class LLMProvider(Protocol):
    def chat(self, messages, schema=None, temperature=0.0): ...

def get_llm() -> LLMProvider:        # selected by env LLM_PROVIDER
    return {
        "gemini":  GeminiAdapter,    # langchain_google_genai
        "openai":  OpenAIAdapter,    # langchain_openai
        "ollama":  OllamaAdapter,    # local open-source (llama3.1, qwen2.5)
        "fake":    FakeAdapter,      # tests
    }[settings.LLM_PROVIDER]()
```

Default `gemini` (free tier → good for a public portfolio). `ollama` lets the whole app run **offline/free** on a
laptop, which is a strong demo point. Swapping providers is a one-line env change — no agent code touches an SDK.
