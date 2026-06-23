# FitTwin 🏋️‍♂️⚡

> **A Multi-Agent AI Fitness & Nutrition Coach with Adaptive Planning and Progress Intelligence**

FitTwin is your **digital training twin**. You tell it who you are and where you want to go; a team of
collaborating AI agents builds your nutrition and training plan, watches your weekly numbers, and *re-plans
on its own* when you stall — while a safety agent makes sure none of it puts you at risk.

It is built as a **portfolio-grade, production-shaped** full-stack application to demonstrate multi-agent
orchestration, FastAPI backend engineering, modern React, document-database modeling, and real system design.

---

## ✨ The one-line pitch (resume version)

> **FitTwin** — a production-style, full-stack **multi-agent AI fitness coach** (LangGraph + FastAPI + React)
> where six specialized agents (Orchestrator, Nutrition, Workout, Progress, Motivation, Safety) collaborate over
> a shared graph state to generate personalized nutrition/training plans, detect plateaus from logged data, and
> **adapt plans weekly** — with JWT auth/RBAC, MongoDB (Beanie) persistence, LangSmith observability, a
> provider-agnostic LLM layer (Gemini/OpenAI/Ollama), and a distinctive 3D/animated UI. Dockerized end-to-end.

(Three more length variants are in [`docs/07-roadmap.md`](docs/07-roadmap.md#resume-worthy-descriptions).)

---

## Why this project is interesting (the engineering story)

| Skill it demonstrates | Where it shows up |
|---|---|
| **Multi-agent systems** | 6 agents over a typed LangGraph state machine with conditional routing |
| **Agent orchestration** | Orchestrator routes queries → sub-agents → reducer; safety as a *gate*, not a step |
| **Backend engineering** | FastAPI, layered architecture (router → service → agent → repository), DI |
| **System design** | HLD, sequence/agent/deployment diagrams, scaling & failure modes |
| **Database design** | MongoDB document modeling, embedding-vs-referencing decisions, indexes |
| **LLM integration** | Provider-agnostic adapter, structured outputs, deterministic tools for math |
| **Security** | JWT access/refresh, Argon2 hashing, RBAC, rate limiting, input validation |
| **Observability** | Structured logging, request IDs, LangSmith agent traces, health/metrics |
| **Product engineering** | Adaptive weekly re-planning loop, shareable progress recap videos |

---

## What makes it *not* look like every other AI app

- **No dark-purple gradient.** An **athletic-performance** design language: bone-white canvas, near-black ink,
  **electric volt-green** energy accent, coral streaks, teal data viz. See [`docs/06-design-system.md`](docs/06-design-system.md).
- A **3D "digital twin"** (React Three Fiber) on the dashboard that fills/energizes as you hit goals.
- **Framer Motion** micro-interactions everywhere; **Remotion** auto-renders a shareable weekly recap video.

---

## Tech stack

**Frontend:** React + Vite · React Router · Tailwind · shadcn/ui · TanStack Query · Recharts · Framer Motion · React Three Fiber · Remotion
**Backend:** Python · FastAPI · Pydantic v2 · **Beanie (MongoDB ODM)** · Motor
**AI:** LangGraph · LangChain · provider-agnostic LLM (Gemini / OpenAI / Ollama) · LangSmith (traces)
**Infra:** Docker · Docker Compose · GitHub Actions (CI)

> **Stack note:** the original spec listed *SQLAlchemy + MongoDB*, which is contradictory (SQLAlchemy is a SQL
> ORM). We standardize on **MongoDB + Beanie** to keep Pydantic and satisfy "MongoDB schemas." Rationale and the
> Postgres alternative are in [`docs/03-data-model.md`](docs/03-data-model.md#why-mongodb-and-not-sqlalchemy).

---

## Documentation map

| Doc | Contents |
|---|---|
| [`docs/01-system-architecture.md`](docs/01-system-architecture.md) | High-level architecture, sequence/deployment/docker diagrams, scaling, failure modes |
| [`docs/02-multi-agent-system.md`](docs/02-multi-agent-system.md) | All 6 agents, LangGraph state & graph, routing, collaboration flows, prompts |
| [`docs/03-data-model.md`](docs/03-data-model.md) | MongoDB collections, ER diagram, embed-vs-reference, indexes |
| [`docs/04-backend.md`](docs/04-backend.md) | Folder structure, layers, DI, full API surface, auth, security, observability |
| [`docs/05-frontend.md`](docs/05-frontend.md) | Folder structure, component hierarchy, state, API integration, pages |
| [`docs/06-design-system.md`](docs/06-design-system.md) | Visual identity, tokens, motion, 3D twin, Remotion recap |
| [`docs/07-roadmap.md`](docs/07-roadmap.md) | Roadmap, sprint plan, feature prioritization (RICE), V2/V3, resume copy |

---

## Quickstart (target developer experience)

```bash
git clone https://github.com/Ryanrezzz/FitTwin && cd FitTwin
cp .env.example .env            # set LLM_PROVIDER + API key, JWT secret, MONGO_URI
docker compose up --build       # api:8000, web:5173, mongo:27017, mongo-express:8081
# open http://localhost:5173
```

See [`docs/01-system-architecture.md#4-docker-architecture`](docs/01-system-architecture.md).

### Run the backend today

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python demo.py                  # zero-setup, fully offline walkthrough of the 6-agent graph
pytest                          # 54 tests (agent core + API + auth), all offline
```

**Use the live API** (auth + persistence need MongoDB; the LLM stays the offline **fake** by default):

```bash
docker run -d -p 27017:27017 --name fittwin-mongo mongo:7   # or point MONGO_URI at Atlas
uvicorn app.main:app --reload                               # http://localhost:8000 — docs at /docs

# register → login → onboard → generate a plan
curl -s localhost:8000/api/v1/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"alex@example.com","password":"supersecret1"}'
TOKEN=$(curl -s localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"alex@example.com","password":"supersecret1"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -X PUT localhost:8000/api/v1/profile -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Alex","age":28,"sex":"male","height_cm":178,"weight_kg":82,"goal":"lose",
       "activity_level":"moderate","experience":"beginner","equipment":["dumbbells"],"training_days":4}'
curl -s -X POST localhost:8000/api/v1/plans/generate -H "Authorization: Bearer $TOKEN"
```

> Without Mongo the API still boots in **degraded mode**: `GET /health` and `python demo.py` work; auth/profile
> routes return `503` until a database is reachable.

Endpoints: `/api/v1/auth/{register,login,refresh,me}` · `GET|PUT /api/v1/profile` ·
`POST /api/v1/plans/generate` · `POST /api/v1/plans/weekly-review` · `POST /api/v1/chat` ·
`GET /health` · `GET /api/v1/health/ready`. All coach/profile routes require `Authorization: Bearer <access>`.

---

## Project status

🟢 **Design phase complete** — full architecture, data model, API surface, agent workflow, frontend/design
system, and roadmap are documented in [`docs/`](docs/). Implementation follows the sprint plan in
[`docs/07-roadmap.md`](docs/07-roadmap.md).

🟢 **AI core + API (Sprint 2)** — the 6-agent LangGraph (deterministic nutrition/progress tools, provider-agnostic
LLM with an offline **fake** provider, safety gate) is built and tested, and now exposed over a **FastAPI** layer
(`router → service → agent`, request-id tracing, consistent error envelope).

🟢 **Auth + persistence (Sprints 0–1)** — **JWT** access/refresh with **Argon2id** hashing, **MongoDB/Beanie**
`User` + `Profile` documents behind a repository layer, RBAC scaffolding, and onboarding via `PUT /profile`.
Coach routes are authenticated and read the user's stored profile. DB init degrades gracefully when Mongo is down;
tests inject in-memory repos so the whole stack runs offline.

🟡 **Next:** persist versioned plans + daily logs, SSE streaming on `/chat` and the scheduled weekly-review worker
(Sprint 4), then the React frontend (Sprint 5).

## License

MIT — see [`LICENSE`](LICENSE).
