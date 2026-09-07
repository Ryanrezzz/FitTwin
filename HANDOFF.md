# FitTwin — Session Handoff / State of the Build

> **Purpose:** a fresh Claude (or developer) should be able to read this and know exactly
> what exists, how to run it, the non-obvious decisions, and what to build next.
> Design intent lives in [`docs/`](docs/); this file is *current reality*.
> `README.md` is the public/GitHub-facing version of the same picture.

---

## 0. TL;DR — where we are

A working full-stack **multi-agent AI fitness coach**, India-first:

- **Backend** (FastAPI, `router → service → agent/repository`): auth (JWT + Argon2 + rate limiting),
  profile/onboarding, **versioned plans**, daily logging, **bodyweight tracking**, **meal rotation**,
  a derived dashboard summary, and a **7-node LangGraph** coach — on MongoDB/Beanie.
- **Frontend** (React + Vite, **JavaScript** — *not* TS): auth → onboarding → dashboard
  (overview cards, week strip, quick-log, **weight card + sparkline**, **rotatable meals**, plan,
  agent map) → AI coach chat.
- **139 backend tests pass** (offline via in-memory repos; 3 DB-integration tests need Mongo).
- Frontend production build is clean; verified rendering in a real browser (no console errors).

**LLM is currently OpenAI `gpt-5.6-luna`** (see §3). `backend/.env` is git-ignored.

---

## 1. Run it (local dev)

Three things must run: **MongoDB**, the **backend** (:8000), the **frontend** (:5173).

```bash
brew services start mongodb-community                             # status: brew services list

cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000 --reload   # docs at /docs
cd frontend && npm run dev                                        # http://localhost:5173
```

Use **`localhost`**, not `127.0.0.1` — Vite binds IPv6.
Tests: `cd backend && .venv/bin/python -m pytest` → **139 passed**.

---

## 2. ⚠️ Critical gotchas (read before editing)

1. **Frontend is plain JavaScript (`.jsx`/`.js`), NOT TypeScript.** Overrides `docs/05`/`06`. User preference.
2. **`env_file=".env"` in `app/config.py` is relative to the process CWD**, so the backend reads
   **`backend/.env`** — *not* the repo-root `.env`. A key added to the root file is silently ignored.
   This has already cost one debugging session.
3. **Beanie 2.x uses PyMongo's native async driver** (`pymongo.AsyncMongoClient`), **not Motor**.
4. **LLM circuit-breaker:** every LLM call falls back to deterministic output on any error
   (`app/ai/llm.py`). The app *always works*. **The trap:** a bad key or model name fails **silently** —
   you get canned template output with no error. Check `get_llm().name` is not `"fake"` when debugging.
5. **Health-critical numbers are always deterministic** — BMR/TDEE/macros/plateau/safety floors are
   tool-computed. The LLM only picks dishes/exercises and writes prose.
6. **🔑 The Gemini key in git history was pasted into chat → treat as leaked. Still not rotated.**
   Rotate/delete it in Google AI Studio.
7. **Test strategy is offline:** in-memory repo fakes via `app.dependency_overrides`, `DB_ENABLED=false`.
   `mongomock-motor` is **incompatible** with Beanie 2.x. `RATE_LIMIT_ENABLED=false` in `conftest.py`
   (the suite logs in constantly); `tests/test_ratelimit.py` switches it back on.
8. **Mongo down?** API boots in **degraded mode**: `/health` + agent core work; data routes return `503`.

---

## 3. LLM configuration (changed — read this)

`backend/.env` now runs **OpenAI**:

```
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-luna
LLM_SEED=42
```

**`gpt-5.6-luna` rejects every temperature except the default (1).** LangChain *silently discards* our
`temperature=0.0` (the attribute becomes `None` and never reaches the payload), so temperature does nothing
and output drifts between identical runs. **`seed` is what pins it down** — `llm_seed` in `config.py`, passed
in `_build_openai()`. Verified: three identical calls now return identical text.

Seed is best-effort (`system_fingerprint` comes back null). For contractual determinism, `gpt-5.4`, `gpt-4.1`
and `gpt-4o` accept `temperature=0`; `gpt-5.5` and `gpt-5.6-*` do not.

`GEMINI_API_KEY` is still present, so switching back is a one-line edit.

---

## 4. Backend — structure & API

Layered: `app/api/routes` → `app/services` / `app/agents` → `app/repositories` → `app/models`.
DI in `app/deps.py`; config in `app/config.py`; resilient DB init in `app/db.py`.

### Endpoints (`/api/v1`, bearer-auth except auth + health)

| Method | Path | Notes |
|---|---|---|
| GET | `/health`, `/health/ready` | liveness; ready reports graph compiled |
| POST | `/auth/register` · `/auth/login` · `/auth/refresh` | **rate-limited** (5/hr, 8/5min, 30/5min) |
| **POST·GET** | **`/auth/google` · `/auth/google/config`** | **Google Sign-In** (20/5min); config gates the UI button |
| GET | `/auth/me` | current user |
| GET·PUT | `/profile` | onboarding profile |
| POST | `/plans/generate` | nutrition + workout + safety → persists a new Plan version |
| POST | `/plans/weekly-review` | **reads stored weigh-ins/logs** when the body is empty |
| POST | `/chat` | free text → orchestrator → specialists |
| GET | `/plans/active` · `/plans/{id}` | versioned plans, user-scoped |
| GET | `/dashboard/summary` | derived cards + today's meals (honours rotations) + agent map |
| GET·PUT | `/logs/today` · GET `/logs/history?days=` | daily logging |
| **GET·PUT** | **`/progress/weight`** | **bodyweight series** |
| **POST** | **`/meals/rotate` · `/meals/rotate/reset`** | **swap one meal slot for today** |

### Collections (`app/models/`)

`users` · `profiles` · `plans` (versioned) · `daily_logs` · **`progress_entries`** · **`meal_rotations`**
— all with unique/compound indexes.

`users` now carries `google_sub`, `email_verified`, `display_name`, `avatar_url`, and **`password_hash` is
optional** (Google-only accounts have none).

---

## 5. The multi-agent system

LangGraph in `app/agents/`: `route` → specialists → `safety` gate → `compose`.

```
START → route ─┬─ progress ─(plateau?)─→ [nutrition, workout] ─┐
               ├─ nutrition ────────────────────────────────────┤
               ├─ workout ──────────────────────────────────────┤→ safety → compose → END
               ├─ motivation ───────────────────────────────────┤
               ├─ answer (Q&A)  ← NEW ──────────────────────────┤
               └─ safety (direct) ──────────────────────────────┘
```

Classification (`registry.py`): **rule** = Progress, Safety · **llm** = Nutrition, Motivation, Coach ·
**hybrid** = Workout. Runner: `app/agents/runner.py::run_coach(...)`.

---

## 6. The food catalog (`app/agents/data/foods_in.py`)

**The problem it fixed:** meal calories were `daily_target × meal_fraction` — a *budget* printed beside an
unrelated dish name. Two different diets produced identical kcal, which was the tell. Nothing measured food.

**Now:** 90 ingredients (IFCT/USDA reference values, ±10%) → **111 dish recipes** (28 breakfast / 30 lunch /
23 snack / 30 dinner). `meal_builder.py` hard-filters by diet+allergens, ranks by kcal *and* protein fit,
biases by age, scales portions to the slot budget, rounds to servable amounts, and reports the macros of the
**rounded plate**.

**Diet is a lattice:** `vegan ⊂ veg ⊂ egg ⊂ nonveg`. One tag per dish; visible to every diet above it. This
structurally fixed a live bug where **eggetarians were served chicken** (the old three-bank design had no
slot for `egg`, so it fell through to omnivore). An unknown diet string now falls back to `veg`, never nonveg.

**Option C contract:** the LLM is handed a pre-filtered menu and returns **dish IDs only** — never numbers.
An ID outside the user's diet is discarded, not obeyed. That's why no fuzzy text matching is needed.

**Portion caps** (`_CAP_BY_FOOD`) exist because scaling alone produced *"rohu fish 360g"* — arithmetically
on-target, nobody's dinner. **Protein top-up:** hitting 2 g/kg on Indian vegetarian food needs a deliberate
booster; it goes to whichever of breakfast/snack is furthest under budget (putting it all on the snack made a
"light" 220 kcal slot into 455 kcal).

**Meal rotation** stores an **index, not a dish id** (`meal_rotations`), so it re-applies to the freshly
filtered candidate list — a stored rotation can never resurrect a dish the user is no longer allowed.
Rotating one slot nudges other meals' *portions* (the day rebalances) but never their *dish*.

---

## 7. Recent work (this session)

- **Age-aware workouts** — bands <30 / 30–49 / 50+; joint-friendly swaps, rep/set changes, explosive finisher
  for the young band. Age also reaches the nutrition prompt and dish scoring.
- **Food catalog + meal rotation + bodyweight tracking** (§4, §6).
- **Security:** per-IP rate limiting; prod guard refusing to boot with a default/short `JWT_SECRET` or
  wildcard CORS; security headers. Fixed the error envelope **dropping `exc.headers`**, which had been
  swallowing `WWW-Authenticate` on every 401 and `Retry-After` on 429.
- **Weekly review reads stored history** instead of requiring the client to send weigh-ins it never had.
- **AI Coach rebuilt.** It was badly broken: `classify_intent` fell through to `general`, which routed to
  Progress, so *every* unrecognised message returned a Weekly Report — "how much protein?", "my knee hurts"
  and "hi" all produced the same trend statistics. `"protein"` wasn't in the nutrition keywords and no
  injury keyword existed. `compose_final` never rendered `meal_plan`, so "what should I eat?" returned
  macros with no food. Fixes: new **`answer` Q&A node** (LLM prose, numbers injected from the stored plan);
  `injury` + `greeting` intents; factual look-ups ("how much…") split from plan requests; meals rendered;
  safety warnings no longer stapled to every reply. Greeting keywords match the whole message only —
  `"hi"` was matching inside *"which"* and `"hey"` inside *"they"*.
- **Frontend:** rotate buttons + Reset, weight card with SVG sparkline, meal portions as wrapping chips
  (they were being `truncate`d), `MEAL_TINT` re-keyed on `slot` (the "Snack" → "Evening Snack" rename had
  silently killed its colour), and an **ErrorBoundary** (a render crash previously blanked the whole app).

---

## 7b. Google Sign-In (`app/core/google_oauth.py`)

Chosen over an email reset flow: free, no email deliverability setup (SPF/DKIM), and it removes the
forgotten-password problem for anyone who uses it.

**Non-obvious bits:**

- **`aud` is the security check.** `verify_oauth2_token(..., settings.google_client_id)` is what stops a
  valid Google token *for another app* being replayed at us. Omitting the audience is the classic OAuth hole.
- **`google_sub` is the join key, not email** — a Google account can change its address; matching on email
  alone is how takeover bugs happen. Linking to an existing password account requires
  `email_verified`, which the verifier enforces before returning.
- **Linking is additive** — an existing password keeps working; users end up with both providers.
- **`password_hash` is now `str | None`.** `authenticate()` rejects a missing hash *explicitly*; treating
  "no hash" as "no password required" would be a full auth bypass. Tested.
- **The `google_sub` index is PARTIAL, not sparse.** Beanie writes `google_sub: null` rather than omitting
  the field, and sparse only skips *missing* fields — so `unique + sparse` made every password user collide
  on null. This actually broke a test before it was caught; the fix is
  `partialFilterExpression={"google_sub": {"$type": "string"}}`.
- Blank `GOOGLE_CLIENT_ID` disables the feature cleanly: `/auth/google` returns 503 and the SPA button
  renders nothing (it reads `/auth/google/config`), rather than showing a button that fails on click.

---

## 8. What's NOT done — prioritized

1. **Password reset / change-password for email accounts.** Google users are covered (Google handles their
   recovery), but password accounts still have *no* recovery path, and nobody can change their password.
   Recommended order: a `manage.py reset-password` CLI (~20 min, the operator escape hatch and the only
   thing that helps if the user also loses their email), then change-password, then the emailed reset —
   which needs: identical response whether or not the email exists (else it's an enumeration oracle),
   DB-hashed single-use tokens, ~30 min expiry, and an email sender (none integrated).
2. **Rotate the leaked Gemini key** (§2.6).
3. **Auth hardening** — httpOnly cookies instead of `localStorage`; server-side token revocation (logout
   currently only clears the browser).
4. **Chat memory** — every message is independent; follow-ups like "and carbs?" have no context.
   No `Conversation`/`AgentRun` persistence.
5. **Split `DashboardPage.jsx`** — ~800 lines against a 121-line component kit.
6. **Docker + docker-compose + CI** — none. **No frontend tests.**
7. **Observability** — structlog / LangSmith / `/metrics` all unwired despite `.env.example` entries.
8. **SSE streaming** on `/chat`; dashboard time-series charts.
9. **DB hygiene** — ~16 accounts, most throwaway test users.
10. **Stretch:** 3D twin (R3F), Remotion recap, dark theme.

---

## 9. Tests

`backend/tests/` — **139 passed**. `conftest.py` provides in-memory fakes for every repo (user, profile,
plan, log, progress, rotation) + auth fixtures; `pyproject.toml` sets `asyncio_mode = "auto"`.

Newer suites: `test_meal_builder.py` (diet lattice, allergens, portions, LLM-choice validation),
`test_meal_rotation.py` (isolation, persistence, can't escape diet, wrapping),
`test_progress_weight.py` (series, dashboard tracking, plateau from stored data),
`test_ratelimit.py`, `test_coach_answers.py` (the coach answers what was asked).

Lint: `ruff check app tests` — clean except ~10 pre-existing errors in
`domain.py`, `models/user.py`, `motivation.py`, `progress.py`, `safety.py`, `tools/progress_math.py`,
`tests/test_graph.py`.

---

## 10. Env (`backend/.env`, git-ignored)

```
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-luna
OPENAI_API_KEY=<set>
GEMINI_API_KEY=<set — LEAKED, rotate>
LLM_SEED=42
DB_ENABLED=true
MONGO_URI=mongodb://localhost:27017
MONGO_DB=fittwin
JWT_SECRET=<dev-only; prod boot is refused if this is the default or <32 chars>
RATE_LIMIT_ENABLED=true      # conftest sets false
```

`.env.example` (committed) documents all settings. `LLM_PROVIDER=fake` runs with zero cost/key.
