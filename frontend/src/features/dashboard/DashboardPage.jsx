import { Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Cpu, Flame, RefreshCw, Sparkles, Utensils } from "lucide-react";
import { Button, Card, Spinner } from "../../components/ui.jsx";
import { useProfile } from "../profile/profile.api";
import { useActivePlan, useDashboardSummary, useGeneratePlan } from "./plan.api";

const spring = { type: "spring", stiffness: 420, damping: 32 };

/** A compact overview tile: big number, optional unit, progress bar and subtext. */
function StatCard({ label, value, unit, sub, accent = "var(--color-teal)", progress }) {
  return (
    <Card className="p-4">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-soft">{label}</div>
      <div className="mt-1 flex items-end gap-1">
        <span className="stat-number text-3xl leading-none">{value}</span>
        {unit && <span className="mb-0.5 text-sm font-semibold text-ink-soft">{unit}</span>}
      </div>
      {progress != null && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line">
          <div
            className="h-full rounded-full transition-[width] duration-700"
            style={{ width: `${Math.min(Math.max(progress, 0), 1) * 100}%`, background: accent }}
          />
        </div>
      )}
      {sub && <div className="mt-1.5 text-xs text-ink-soft">{sub}</div>}
    </Card>
  );
}

function OverviewCards({ s }) {
  const consumed = s.calorie_target - s.calories_remaining;
  const proteinDone = s.protein_target_g - s.protein_remaining_g;
  const waterL = (s.water_ml / 1000).toFixed(1);
  const waterGoalL = (s.water_goal_ml / 1000).toFixed(1);
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard label="Current weight" value={s.current_weight_kg} unit="kg" sub={`Goal: ${s.goal}`} />
      <StatCard
        label="Target weight"
        value={s.target_weight_kg}
        unit="kg"
        accent="var(--color-volt-press)"
        sub={s.est_goal_weeks ? `~${s.est_goal_weeks} wks to go` : "You're in range"}
      />
      <StatCard
        label="Calories left"
        value={s.calories_remaining}
        unit="kcal"
        accent="var(--color-coral)"
        progress={consumed / s.calorie_target}
        sub={`of ${s.calorie_target} kcal`}
      />
      <StatCard
        label="Protein left"
        value={s.protein_remaining_g}
        unit="g"
        progress={proteinDone / s.protein_target_g}
        sub={`of ${s.protein_target_g} g`}
      />
      <StatCard
        label="Water"
        value={waterL}
        unit="L"
        progress={s.water_ml / s.water_goal_ml}
        sub={`goal ${waterGoalL} L`}
      />
      <StatCard
        label="Steps"
        value={s.steps.toLocaleString()}
        accent="var(--color-volt-press)"
        progress={s.steps / s.step_goal}
        sub={`goal ${s.step_goal.toLocaleString()}`}
      />
      <StatCard
        label="Workouts"
        value={`${s.workout_completion_pct}%`}
        accent="var(--color-volt-press)"
        progress={s.workout_completion_pct / 100}
        sub={`${s.workouts_done}/${s.workout_target_days} this week`}
      />
      <StatCard
        label="Streak"
        value={s.streak_days}
        unit="days"
        accent="var(--color-coral)"
        sub={s.streak_days ? "🔥 keep it going" : "Log today to start"}
      />
    </div>
  );
}

const MODE_BADGE = {
  rule: { label: "Rule-based", cls: "bg-teal/15 text-teal" },
  llm: { label: "LLM", cls: "bg-volt/30 text-ink" },
  hybrid: { label: "Hybrid", cls: "bg-amber/20 text-amber" },
};
const ENGINE_LABEL = {
  rule: "Rule-based (offline)",
  gemini: "Gemini",
  openai: "OpenAI",
  local: "Local · Ollama",
};

/** Surfaces the hybrid decision: which agents are plain Python vs LLM-powered. */
function CoachingEngine({ engine, agents }) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-display text-lg font-bold">
          <Cpu className="size-4 text-volt-press" /> Coaching engine
        </h3>
        <span className="rounded-full bg-ink/5 px-2.5 py-1 text-xs font-medium text-ink-soft">
          model: {ENGINE_LABEL[engine] ?? engine}
        </span>
      </div>
      <p className="mt-1 text-sm text-ink-soft">
        Each agent runs as plain Python rules, an LLM, or a hybrid of both.
      </p>
      <div className="mt-4 space-y-2">
        {agents.map((a) => {
          const m = MODE_BADGE[a.mode] ?? MODE_BADGE.rule;
          return (
            <div key={a.key} className="flex items-start justify-between gap-3 rounded-[12px] border border-line p-3">
              <div>
                <div className="font-semibold">{a.name}</div>
                <div className="text-xs text-ink-soft">{a.blurb}</div>
              </div>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${m.cls}`}>
                {m.label}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function MacroSplit({ macros }) {
  const p = macros.protein_g ?? 0;
  const c = macros.carbs_g ?? 0;
  const f = macros.fat_g ?? 0;
  const kcal = { p: p * 4, c: c * 4, f: f * 9 };
  const total = kcal.p + kcal.c + kcal.f || 1;
  const rows = [
    { label: "Protein", g: p, kcal: kcal.p, color: "var(--color-teal)" },
    { label: "Carbs", g: c, kcal: kcal.c, color: "var(--color-volt-press)" },
    { label: "Fat", g: f, kcal: kcal.f, color: "var(--color-coral)" },
  ];
  return (
    <div className="space-y-3">
      <div className="flex h-3 overflow-hidden rounded-full bg-line">
        {rows.map((r) => (
          <div key={r.label} style={{ width: `${(r.kcal / total) * 100}%`, background: r.color }} />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-3">
        {rows.map((r) => (
          <div key={r.label}>
            <div className="flex items-center gap-1.5 text-xs text-ink-soft">
              <span className="size-2 rounded-full" style={{ background: r.color }} />
              {r.label}
            </div>
            <div className="stat-number text-2xl">
              {r.g}
              <span className="ml-0.5 text-sm font-semibold text-ink-soft">g</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TwinHero({ name, goal, calories }) {
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute -right-10 -top-10 size-48 rounded-full bg-volt/40 blur-2xl" />
      <div className="absolute right-6 bottom-0 size-28 rounded-full bg-teal/30 blur-2xl" />
      <div className="relative">
        <div className="flex items-center gap-2 text-sm font-medium text-ink-soft">
          <Sparkles className="size-4 text-volt-press" /> Your digital twin
        </div>
        <h2 className="mt-1 font-display text-3xl font-extrabold tracking-tight">
          Hey {name || "athlete"} 👋
        </h2>
        <p className="mt-1 text-ink-soft">
          Goal: <span className="font-semibold text-ink">{goal}</span>
        </p>
        <div className="mt-5 flex items-end gap-2">
          <span className="stat-number text-5xl">{calories}</span>
          <span className="mb-1 text-sm font-semibold text-ink-soft">kcal / day target</span>
        </div>
      </div>
    </Card>
  );
}

function WorkoutCard({ workout }) {
  return (
    <Card>
      <h3 className="font-display text-lg font-bold">Training</h3>
      <p className="text-sm text-ink-soft">{workout.split}</p>
      <div className="mt-4 space-y-3">
        {(workout.sessions ?? []).map((s, i) => (
          <div key={i} className="rounded-[12px] border border-line p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-semibold">{s.day}</span>
              <span className="rounded-full bg-ink/5 px-2 py-0.5 text-xs font-medium text-ink-soft">
                {s.focus}
              </span>
            </div>
            <ul className="space-y-1">
              {(s.exercises ?? []).map((ex, j) => (
                <li key={j} className="flex justify-between text-sm">
                  <span>{ex.name}</span>
                  <span className="text-ink-soft">
                    {ex.sets} × {ex.reps}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  );
}

function MealsCard({ nutrition }) {
  const meals = nutrition.meal_plan ?? [];
  if (meals.length === 0) return null;
  return (
    <Card>
      <h3 className="flex items-center gap-2 font-display text-lg font-bold">
        <Utensils className="size-4 text-teal" /> Meal plan
      </h3>
      <div className="mt-4 space-y-3">
        {meals.map((m, i) => (
          <div key={i} className="rounded-[12px] border border-line p-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold">{m.name}</span>
              <span className="text-sm text-ink-soft">
                {m.kcal} kcal · {m.protein_g}g P
              </span>
            </div>
            <p className="mt-1 text-sm text-ink-soft">{(m.items ?? []).join(", ")}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: profile, isLoading: loadingProfile } = useProfile();
  const { data: plan, isLoading: loadingPlan } = useActivePlan();
  const { data: summary } = useDashboardSummary(!!profile);
  const generate = useGeneratePlan();

  if (loadingProfile) return <Spinner label="Loading…" />;
  if (!profile) return <Navigate to="/onboarding" replace />;
  if (loadingPlan) return <Spinner label="Loading your plan…" />;

  if (!plan) {
    return (
      <div className="mx-auto max-w-lg text-center">
        <Card>
          <Flame className="mx-auto size-8 text-coral" />
          <h2 className="mt-3 font-display text-2xl font-extrabold">Wake up your twin</h2>
          <p className="mt-1 text-ink-soft">
            Generate your first nutrition + training plan from your profile.
          </p>
          <Button
            className="mt-5"
            loading={generate.isPending}
            onClick={() => generate.mutate()}
          >
            <Sparkles className="size-4" /> Generate my plan
          </Button>
          {generate.isError && <p className="mt-3 text-sm text-coral">{generate.error.message}</p>}
        </Card>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={spring}
      className="space-y-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-ink-soft">
          <span className="rounded-full bg-ink/5 px-2.5 py-1 font-medium">Plan v{plan.version}</span>
          {plan.degraded && (
            <span className="rounded-full bg-amber/20 px-2.5 py-1 font-medium text-amber">
              fallback
            </span>
          )}
        </div>
        <Button variant="outline" loading={generate.isPending} onClick={() => generate.mutate()}>
          <RefreshCw className="size-4" /> Regenerate
        </Button>
      </div>

      {summary && <OverviewCards s={summary} />}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TwinHero name={profile.name} goal={profile.goal} calories={plan.calorie_target} />
        </div>
        <Card>
          <h3 className="font-display text-lg font-bold">Daily macros</h3>
          <div className="mt-4">
            <MacroSplit macros={plan.macros} />
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <MealsCard nutrition={plan.nutrition ?? {}} />
        <WorkoutCard workout={plan.workout ?? {}} />
      </div>

      {summary && <CoachingEngine engine={summary.engine} agents={summary.agents} />}
    </motion.div>
  );
}
