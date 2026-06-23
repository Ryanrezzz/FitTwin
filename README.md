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

---

## Project status

🟢 **Design phase complete** — full architecture, data model, API surface, agent workflow, frontend/design
system, and roadmap are documented in [`docs/`](docs/). Implementation follows the sprint plan in
[`docs/07-roadmap.md`](docs/07-roadmap.md).

## License

MIT — see [`LICENSE`](LICENSE).
