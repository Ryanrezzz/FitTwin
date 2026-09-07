# FitTwin 🏋️‍♂️⚡

> **A multi-agent AI fitness & nutrition coach for Indian gym-goers — with adaptive planning, a real food catalog, and a safety gate.**

FitTwin is a **digital training twin**. You tell it who you are and where you want to go; a team of
collaborating agents builds your nutrition and training plan, watches your logged numbers, and **re-plans when
you stall** — while a safety agent makes sure none of it puts you at risk.

The design principle throughout: **agents own judgement, tools own constraints.** Every number a user could be
harmed by — calories, macros, plateau verdicts, safety floors — is computed by deterministic, unit-tested
Python. The LLM chooses *which* dish or exercise, never *how many* calories.

**Status:** working full-stack app. Backend, frontend, agents and persistence all run locally. **139 backend
tests pass.** See [What's built](#whats-built) for an honest line between done and not-done.

---

## Contents

- [What it does](#what-it-does) · [Run it](#run-it) · [How the agents work](#how-the-agents-work)
- [The food catalog](#the-food-catalog) · [What's built](#whats-built) · [API](#api) · [Docs](#documentation)

---

## What it does

**Age-aware training.** A 24-year-old and a 58-year-old with identical experience and equipment get different
sessions — not the same plan with different wording:

| | 24, intermediate, full gym | 58, intermediate, full gym |
|---|---|---|
| Press | Bench Press 4×6-10 | **DB** Bench Press **3×8-12** |
| Row | Barbell Row | **Chest-Supported DB** Row |
| Extra | **+ Plyo Push-ups** (explosive finisher) | — |
| Coaching | "train close to your limit" | "warm up 8–10 min, extra rest day" |

**Meals whose numbers describe the food.** Every meal is composed from a catalog of real ingredients, so its
calories are *summed from the portions listed* rather than asserted next to them:

```
Breakfast   613 kcal  39g P   4 x egg, oats (dry) 55g, toned milk 150ml
Lunch       798 kcal  73g P   chicken breast 205g, rice (dry) 95g, curd 100g, oil 8g
```

**Rotate any meal.** Don't want fish tonight? Swap that one slot — the rest of the day stays put and the day
stays on target. Rotation persists, and can never hand you something your diet or allergies forbid.

**A coach that answers the question.** "How much protein should I eat?" returns *"Aim for 180 g per day"* —
grounded in your stored plan, not invented by the model.

---

## Run it

Three things run: **MongoDB**, the **API** (`:8000`), the **web app** (`:5173`).

```bash
git clone https://github.com/Ryanrezzz/FitTwin && cd FitTwin
```

**1 · MongoDB** — pick one:

```bash
brew services start mongodb-community          # macOS native
docker run -d -p 27017:27017 --name fittwin-mongo mongo:7
# or point MONGO_URI at a free MongoDB Atlas cluster
```

**2 · Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env          # works as-is: LLM_PROVIDER=fake needs no API key
uvicorn app.main:app --reload    # http://localhost:8000 — OpenAPI docs at /docs
```

**Optional — Sign in with Google.** Create an OAuth *Web application* client in Google Cloud Console with
`http://localhost:5173` as an authorized JavaScript origin, then set `GOOGLE_CLIENT_ID` in `backend/.env`.
It's free, and the `email`/`profile` scopes need no Google review. Left blank, the button simply doesn't render.

**3 · Frontend**

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

> Use `localhost`, not `127.0.0.1` — Vite binds IPv6.

Then: **register → onboarding → dashboard → Generate plan → AI Coach**.

### No API key? It still works.

`LLM_PROVIDER=fake` runs the whole app offline and deterministically. Every LLM call falls back to
deterministic output on any error, so the app works with no key, an expired key, or exhausted quota. To use a
real model, set `LLM_PROVIDER` to `gemini`, `openai` or `ollama` and supply the matching key.

### Tests

```bash
cd backend && pytest             # 139 tests; 3 DB-integration tests skip without Mongo
python demo.py                   # zero-setup offline walkthrough of the agent graph
```

Tests inject **in-memory repository fakes**, so the whole suite runs with no database and no API key.

---

## How the agents work

LangGraph state machine, deterministic routing:

```
START → route ─┬─ progress ─(plateau?)─→ [nutrition, workout] ─┐
               ├─ nutrition ────────────────────────────────────┤
               ├─ workout ──────────────────────────────────────┤→ safety → compose → END
               ├─ motivation ───────────────────────────────────┤
               ├─ answer (Q&A) ─────────────────────────────────┤
               └─ safety (direct) ──────────────────────────────┘
```

Safety is a **gate, not a step** — every plan-producing path flows through it. It clamps rather than blocks:
an unsafe target is raised to a safe floor (1500 kcal male / 1200 female) and the macros recomputed.

Agents are classified by how much the model is trusted:

| Mode | Agents | The model's role |
|---|---|---|
| **rule** | Progress, Safety | none — pure Python |
| **hybrid** | Workout | rule core, LLM personalises within available equipment |
| **llm** | Nutrition, Motivation, Coach Q&A | picks dishes / writes prose, grounded in tool numbers |

### Where the numbers come from

Calories are a four-step deterministic chain in
[`nutrition_math.py`](backend/app/agents/tools/nutrition_math.py) — no LLM involved:

```
BMR    = 10×kg + 6.25×cm − 5×age + s        (Mifflin-St Jeor; s = +5 male / −161 female)
TDEE   = BMR × activity multiplier           (1.2 … 1.9)
target = TDEE ∓ (rate_kg_per_week × 7700)/7  (clamped: max 25% deficit / 20% surplus)
macros = protein by bodyweight → fat floor 25% → carbs fill the remainder
```

---

## The food catalog

India-first, and built so a meal's numbers can't lie:

- **90 ingredients** with per-100g (or per-unit) macros, diet tag and allergen tags
- **111 dish recipes** composed from them — 28 breakfast · 30 lunch · 23 snack · 30 dinner
- Portions **scale to the calorie budget**, then round to servable amounts, and the reported macros are
  recomputed from the *rounded* plate

Values are IFCT/USDA reference figures (±10%), not lab assays — planning numbers, documented as such in the
source.

**Diet is a lattice, not four menus:**

```
vegan  ⊂  vegetarian  ⊂  eggetarian  ⊂  nonveg
```

Each dish carries one tag and is visible to every diet above it. Writing `dal_tadka` once as vegan serves all
four. This is also what makes "eggetarian" safe — an earlier three-menu design had no slot for it and served
eggetarians chicken.

Diet and allergens are a **hard pre-filter applied before the LLM sees anything**, so the model is physically
unable to name a forbidden dish. Verified across 14 simulated days × 4 diets, and across every rotation step.

---

## What's built

### ✅ Working

- **6-agent LangGraph** with intent routing, plateau-driven re-planning, and a safety gate
- **Nutrition & workout planning** — age-banded training (<30 / 30–49 / 50+), equipment-aware exercise
  selection, catalog-backed meals
- **Meal rotation** — per-slot swaps that persist and respect diet/allergies
- **Bodyweight tracking** — dated weigh-ins driving the weight card, weeks-to-goal and plateau detection
- **Daily logging** — water, steps, calories, protein, workout completion, plus streaks
- **Versioned plans** — every run persisted; prior versions retained, one active
- **Auth** — **Sign in with Google** (server-verified ID tokens, account linking), JWT access/refresh,
  Argon2id hashing, per-IP rate limiting on credential endpoints
- **React SPA** — auth, onboarding, dashboard, AI coach chat, error boundary
- **139 backend tests**, fully offline

### 🚧 Not built yet

Listed honestly, because this is a portfolio repo and a clone should match its README:

- **No Docker / docker-compose / CI** — run the three processes manually as above
  (a Render blueprint *is* included — see [`DEPLOY.md`](DEPLOY.md))
- **No password reset for email/password accounts** — Google users are unaffected (Google handles their
  recovery), but a forgotten *password* still means a lost account. No change-password endpoint either.
- **No server-side token revocation**; tokens live in `localStorage` (httpOnly cookies are the intended fix)
- **No chat memory** — each message is independent, so follow-ups lack context
- **No SSE streaming** on `/chat`, no charts library, no 3D twin, no observability stack

---

## API

All routes under `/api/v1`, bearer-auth except `/auth/*` and health.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` · `/health/ready` | liveness; ready reports the graph compiled |
| `POST` | `/auth/register` · `/auth/login` · `/auth/refresh` | JWT pair; rate-limited |
| `POST` | `/auth/google` · `GET /auth/google/config` | Google Sign-In; config tells the SPA whether to show it |
| `GET` | `/auth/me` | current user |
| `GET` `PUT` | `/profile` | onboarding profile |
| `POST` | `/plans/generate` | run nutrition + workout + safety, persist a version |
| `POST` | `/plans/weekly-review` | analyse logged history, re-plan on plateau |
| `POST` | `/chat` | free text → orchestrator → specialists |
| `GET` | `/plans/active` · `/plans/{id}` | read versioned plans |
| `GET` | `/dashboard/summary` | derived overview cards, today's meals, agent map |
| `GET` `PUT` | `/logs/today` · `GET /logs/history` | daily logging |
| `GET` `PUT` | `/progress/weight` | bodyweight series |
| `POST` | `/meals/rotate` · `/meals/rotate/reset` | swap one meal slot |

Full interactive docs at `/docs` when the API is running.

---

## Tech stack

**Backend** — Python 3.13 · FastAPI · Pydantic v2 · Beanie (MongoDB ODM, on PyMongo's async driver) ·
LangGraph · LangChain · PyJWT · argon2-cffi

**Frontend** — React 18 · Vite 6 · **JavaScript** (not TypeScript) · React Router · Tailwind v4 ·
TanStack Query · Zustand · Framer Motion · lucide-react

**LLM** — provider-agnostic adapter over Gemini / OpenAI / Ollama, with an offline `fake` provider and a
circuit breaker on every call

> **Stack note:** the original spec listed *SQLAlchemy + MongoDB*, which is contradictory (SQLAlchemy is a SQL
> ORM). This standardises on **MongoDB + Beanie**; rationale in
> [`docs/03-data-model.md`](docs/03-data-model.md).

---

## Documentation

| Doc | Contents |
|---|---|
| [`docs/01-system-architecture.md`](docs/01-system-architecture.md) | Architecture, sequence/deployment diagrams, scaling, failure modes |
| [`docs/02-multi-agent-system.md`](docs/02-multi-agent-system.md) | The agents, graph state, routing, collaboration flows |
| [`docs/03-data-model.md`](docs/03-data-model.md) | Collections, ER diagram, embed-vs-reference, indexes |
| [`docs/04-backend.md`](docs/04-backend.md) | Layers, DI, API surface, auth, security |
| [`docs/05-frontend.md`](docs/05-frontend.md) | Structure, component hierarchy, state, pages |
| [`docs/06-design-system.md`](docs/06-design-system.md) | Visual identity, tokens, motion |
| [`docs/07-roadmap.md`](docs/07-roadmap.md) | Roadmap, sprint plan, prioritisation |
| [`docs/08-domain-nutrition-equipment.md`](docs/08-domain-nutrition-equipment.md) | Equipment taxonomy, food catalog design, personalization signals |

Some documents describe the intended design ahead of the implementation; [What's built](#whats-built) is the
current reality, and [`HANDOFF.md`](HANDOFF.md) tracks state in detail.

---

## Design language

An **athletic-performance** identity rather than the usual AI dark-purple: bone-white canvas, near-black ink,
electric **volt-green** accent, coral for streaks, teal for data. Tokens live in `frontend/src/index.css`.

---

## License

MIT — see [`LICENSE`](LICENSE).
