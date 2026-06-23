# FitTwin — Web (React + Vite)

The SPA frontend, built in **JavaScript** (React + Vite). Athletic "volt-green" design
system (Tailwind v4 tokens), server state via **TanStack Query**, auth tokens via **Zustand**,
motion via **Framer Motion**.

## Run

```bash
# 1) start the backend first (see ../backend) — it must be on http://localhost:8000
# 2) then:
cd frontend
npm install
npm run dev            # http://localhost:5173  (proxies /api → :8000)
```

`npm run build` outputs a static bundle to `dist/`. In production set `VITE_API_BASE_URL`
to the API's public URL (in dev the Vite proxy handles `/api`, so it's left empty).

## Structure (feature-first)

```
src/
├── main.jsx                 # Query + Router + MotionConfig providers
├── App.jsx                  # routes + auth guard
├── index.css                # Tailwind v4 import + design tokens (docs/06)
├── lib/        api.js (fetch + refresh-on-401), queryKeys.js
├── stores/     auth.js (Zustand, persisted access/refresh tokens)
├── components/ ui.jsx (Button/Card/Field/Input/StatRing), AppShell.jsx
└── features/
    ├── auth/         AuthPage + auth.api      (login / register)
    ├── onboarding/   OnboardingPage           (profile form → PUT /profile)
    ├── profile/      profile.api
    ├── dashboard/    DashboardPage + plan.api (active plan, generate/regenerate)
    └── coach/        CoachPage + chat.api     (POST /chat, agent-step trace)
```

## Flow

login/register → (no profile) onboarding → dashboard (generate plan) → AI coach.
The dashboard reads the active versioned plan; the coach routes a message through the
multi-agent graph and shows which agents ran.

## Deferred (per roadmap)

3D digital twin (R3F), Recharts dashboards (need the logs/progress endpoints),
SSE token streaming on chat, and the Remotion recap video.
