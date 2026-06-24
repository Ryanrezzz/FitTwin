# 04 · Backend (FastAPI)

Layered, dependency-injected, and AI-agnostic. The rule: **dependencies point inward and downward** —
`router → service → (agent | repository)`. Routers know HTTP; services know use-cases; agents know reasoning;
repositories know Mongo. Nothing skips a layer.

---

## 1. Folder structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app factory, middleware, router mount, lifespan (DB init)
│   ├── worker.py               # APScheduler entrypoint for weekly reviews
│   ├── config.py               # Pydantic Settings (env-driven)
│   ├── deps.py                 # DI providers (current_user, repos, services, llm)
│   │
│   ├── api/                    # ── ROUTER LAYER (HTTP boundary only)
│   │   ├── routes/
│   │   │   ├── auth.py         # /auth/register, /login, /refresh, /me
│   │   │   ├── profile.py      # /profile  (CRUD)
│   │   │   ├── goals.py        # /goals
│   │   │   ├── plans.py        # /plans (generate/get/version)
│   │   │   ├── logs.py         # /logs (daily logs, food, steps)
│   │   │   ├── progress.py     # /progress (weight, reports, charts data)
│   │   │   ├── chat.py         # /chat (SSE stream to orchestrator)
│   │   │   └── admin.py        # /admin/* (RBAC: admin only)
│   │   └── errors.py           # exception handlers → consistent error envelope
│   │
│   ├── services/               # ── SERVICE LAYER (use-cases, orchestration of repos+agents)
│   │   ├── auth_service.py
│   │   ├── plan_service.py     # generate_plan(), weekly_review() ← drives the graph
│   │   ├── log_service.py
│   │   ├── progress_service.py
│   │   └── chat_service.py     # stream orchestrator output as SSE
│   │
│   ├── agents/                 # ── AGENT LAYER (LangGraph)
│   │   ├── state.py            # AgentState TypedDict
│   │   ├── graph.py            # build + compile the StateGraph
│   │   ├── orchestrator.py
│   │   ├── nutrition.py  workout.py  progress.py  motivation.py  safety.py
│   │   ├── tools/              # DETERMINISTIC tools
│   │   │   ├── nutrition_math.py   # bmr, tdee, calorie_target, macros
│   │   │   ├── progress_math.py    # weight_trend, plateau_detected, adherence
│   │   │   └── food_parser.py      # "250g chicken and rice" → items+macros
│   │   ├── data/               # SEEDED domain catalogs (08): foods_in.py (Indian),
│   │   │                       #   equipment_map.py (movement→capability), archetypes.py
│   │   └── prompts/            # versioned system prompts
│   │
│   ├── ai/
│   │   └── llm.py              # provider adapter (gemini/openai/ollama/fake)
│   │
│   ├── repositories/           # ── REPOSITORY LAYER (only place importing Beanie)
│   │   ├── base.py            user_repo.py  profile_repo.py  plan_repo.py
│   │   ├── log_repo.py        progress_repo.py  conversation_repo.py  agent_run_repo.py
│   │
│   ├── models/                 # Beanie Documents (see 03-data-model.md)
│   ├── schemas/                # Pydantic request/response DTOs (NOT the DB models)
│   ├── core/
│   │   ├── security.py        # Argon2 hashing, JWT encode/decode
│   │   ├── logging.py         # structlog config, request-id binding
│   │   ├── ratelimit.py       # slowapi limiter
│   │   └── observability.py   # LangSmith + Prometheus hooks
│   └── db.py                   # Motor client + Beanie init
├── tests/                      # unit (tools-only, FakeLLM) + integration (testcontainers mongo)
├── Dockerfile                  # multi-stage; shared by api + worker
├── pyproject.toml              # deps via uv/poetry
└── .env.example
```

**Why DTOs separate from models:** `schemas/` (API contract) ≠ `models/` (storage). You never leak
`password_hash`, and the API surface can evolve without a DB migration. This separation is a senior tell.

---

## 2. Dependency injection

FastAPI's `Depends` is the DI container. Layers receive collaborators; nothing news-up a dependency.

```python
# app/deps.py
def get_user_repo() -> UserRepo: return UserRepo()
def get_plan_service(
    plan_repo: PlanRepo = Depends(get_plan_repo),
    profile_repo: ProfileRepo = Depends(get_profile_repo),
    graph = Depends(get_agent_graph),         # compiled LangGraph (singleton)
) -> PlanService:
    return PlanService(plan_repo, profile_repo, graph)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    repo: UserRepo = Depends(get_user_repo),
) -> User:
    payload = decode_access_token(token)       # raises 401 on bad/expired
    user = await repo.get(payload["sub"])
    if not user or not user.is_active: raise unauthorized()
    return user

def require_role(*roles: Role):
    def guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles: raise forbidden()
        return user
    return guard
```

Tests override providers (`app.dependency_overrides`) to inject `FakeLLM` and an ephemeral Mongo — the whole agent
graph runs in CI offline and deterministically.

---

## 3. API surface

Base path `/api/v1`. All non-auth routes require `Authorization: Bearer <access>`.

### Auth
| Method | Path | Body / notes | Returns |
|---|---|---|---|
| POST | `/auth/register` | email, password, name | `201` user (no hash) |
| POST | `/auth/login` | email, password (OAuth2 form) | access + refresh tokens |
| POST | `/auth/refresh` | refresh token | new access token |
| GET | `/auth/me` | — | current user |

### Profile & goals
| Method | Path | Notes |
|---|---|---|
| GET / PUT | `/profile` | full onboarding profile (age, sex, height, weight, activity, diet, allergies, experience, equipment, days) |
| GET / POST | `/goals` | create goal; one `active` at a time |

### Plans (AI generation lives here)
| Method | Path | Notes |
|---|---|---|
| POST | `/plans/generate` | run orchestrator → nutrition+workout+safety → persist v1 |
| GET | `/plans/active` | current versioned plan (meal + workout + targets) |
| GET | `/plans/{id}` | a specific version |
| POST | `/plans/weekly-review` | manual trigger of the adaptive loop (also runs nightly via worker) |

### Logs
| Method | Path | Notes |
|---|---|---|
| GET | `/logs?from&to` | daily logs range (dashboard) |
| PUT | `/logs/{date}` | upsert calories/protein/steps/**water_ml/sleep_hours**/workout_done |
| POST | `/logs/{date}/food` | add food item (uses food_parser tool) |

### Progress
| Method | Path | Notes |
|---|---|---|
| POST | `/progress/weight` | log weight entry |
| GET | `/progress/series?metric=weight\|calories\|protein\|steps&window=` | chart data |
| GET | `/progress/report/latest` | latest weekly report (markdown + metrics) |
| GET | `/progress/recap/{iso_week}.mp4` | Remotion-rendered recap (V1.5) |

### Dashboard (read-only aggregations — see [`05 §5a`](05-frontend.md#5a-dashboard-the-product-surface))

All four are **derived on read** from `daily_logs` / `progress_entries` / active `plan` / `weekly_reports` by the
Progress + Nutrition tools — no new collections (see [`03`](03-data-model.md#profile-document-expanded)). Cheap,
cacheable, and consistent with the chart endpoints.

| Method | Path | Returns |
|---|---|---|
| GET | `/dashboard/summary` | **overview cards**: current_weight, target_weight, calories_remaining, protein_remaining, water_ml, steps, workout_completion_pct, streak_days, est_goal_date |
| GET | `/dashboard/insights` | **AI insights**: `[{severity, text}]` (e.g. "Protein below target 5 days", "~10 weeks to goal") — generated by the Progress agent (rule-based facts; LLM phrasing optional) |
| GET | `/dashboard/nutrition-insights` | avg_calories_week, avg_protein_week, macro_breakdown, meal_adherence_pct |
| GET | `/dashboard/fitness-insights` | total_workouts, total_hours, favorite_muscle_group, most_missed_day |
| GET | `/dashboard/tasks?date=` | **daily-tasks widget**: water / protein / workout / walk / sleep, each `{target, current, done}` |

### Catalog (drives onboarding & nutrition UI)

| Method | Path | Returns |
|---|---|---|
| GET | `/catalog/equipment` | gym-type contexts + the 13-item equipment list ([`08 §1`](08-domain-nutrition-equipment.md#1-equipment-taxonomy)) |
| GET | `/catalog/diet-options` | dietary prefs, allergy presets, budget/lifestyle/cooking tiers, meal-plan archetypes ([`08 §3–4`](08-domain-nutrition-equipment.md#3-meal-plan-archetypes)) |

These are static, cacheable enums served from `app/domain.py` + the seeded catalog so the frontend never hard-codes
domain lists.

### AI Coach chat
| Method | Path | Notes |
|---|---|---|
| GET | `/chat/conversations` | list |
| POST | `/chat/conversations` | new conversation |
| POST | `/chat/conversations/{id}/messages` | **SSE stream**: agent steps + tokens + structured cards |
| GET | `/chat/conversations/{id}/messages` | history |

### Admin (RBAC)
| Method | Path | Role |
|---|---|---|
| GET | `/admin/users` | admin |
| GET | `/admin/agent-runs` | admin/coach (debug traces) |
| GET | `/admin/config` | admin — current **agent execution mode** (`rule \| gemini \| openai \| local`), model id, per-agent mode map ([`02 §0`](02-multi-agent-system.md#0-agent-execution-modes-the-hybrid-architecture)) |

### System
| Method | Path | Notes |
|---|---|---|
| GET | `/health` | liveness (no DB) |
| GET | `/health/ready` | readiness (pings Mongo) |
| GET | `/metrics` | Prometheus |

**Error envelope** (consistent across all routes):
```json
{ "error": { "code": "PLAN_UNSAFE", "message": "Calorie target below safe floor; clamped.", "request_id": "..." } }
```

---

## 4. Security

| Control | Implementation |
|---|---|
| **Password hashing** | **Argon2id** (`argon2-cffi`) — memory-hard, current best practice (bcrypt acceptable fallback). Never store plaintext; never log it. |
| **JWT** | Short-lived **access (15 min)** + rotating **refresh (7 d)**. `sub`, `role`, `exp`, `jti`. Refresh tokens can be revoked via a `jti` denylist (Redis, V1.5). |
| **RBAC** | `require_role(Role.admin)` dependency guards admin routes; `coach` can read traces; `user` owns only their data (object-level check in repos: every query is scoped to `user_id`). |
| **Input validation** | Pydantic v2 schemas on every body/query; reject extra fields; numeric bounds (age 13–100, weight, etc.). |
| **Rate limiting** | `slowapi` — global + tighter buckets on `/auth/*` (brute-force) and `/chat`/`/plans/generate` (LLM cost abuse). Keyed by user id (authed) or IP. |
| **CORS** | Locked to the web origin from env, credentials allowed. |
| **Secrets** | Pydantic `Settings` from env; `.env` git-ignored; `.env.example` committed. |
| **Transport** | TLS terminated at the proxy; HSTS. |
| **AuthZ correctness** | The #1 multi-tenant bug is forgetting `user_id` scoping → every repo method takes `user_id` and filters on it; admin override is explicit. |

---

## 5. Observability & logging

- **Structured logging** with `structlog` → JSON in prod. A middleware mints a **`request_id`** (and `user_id`
  when authed), binds it to the logger context, and echoes it in responses + the error envelope. One id ties an
  HTTP request → service call → agent run → log lines.
- **Agent tracing** via **LangSmith**: every graph invocation is a trace; each node a span with inputs/outputs,
  tokens, latency. You can replay any user's weekly review. Also persisted compactly as `AgentRun.steps`.
- **Metrics** (`prometheus-fastapi-instrumentator`): request latency/throughput/errors + custom counters
  (`plan_generations_total`, `llm_tokens_total`, `safety_clamps_total`, `weekly_reviews_total`).
- **Error tracking**: Sentry in prod for unhandled exceptions with the `request_id` attached.
- **Health**: `/health` (liveness, no deps) vs `/health/ready` (readiness, pings Mongo) so the orchestrator can
  route traffic correctly.

---

## 6. App lifecycle

```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()                 # Motor client + Beanie init_beanie(models=[...])
    app.state.graph = build_graph() # compile LangGraph once (singleton)
    yield
    await close_db()

app = FastAPI(title="FitTwin API", version="1.0", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(CORSMiddleware, ...)
app.state.limiter = limiter
app.include_router(api_v1)          # mounts all routes under /api/v1
```
