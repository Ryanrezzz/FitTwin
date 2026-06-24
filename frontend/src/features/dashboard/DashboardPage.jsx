import { useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { animate, motion, useReducedMotion } from "framer-motion";
import { Cpu, Droplets, Dumbbell, Flame, Footprints, RefreshCw, Sparkles, Utensils } from "lucide-react";
import { Button, Card, Input, Spinner } from "../../components/ui.jsx";
import { useProfile } from "../profile/profile.api";
import { useActivePlan, useDashboardSummary, useGeneratePlan } from "./plan.api";
import { useTodayLog, useUpdateLog } from "./logs.api";

const spring = { type: "spring", stiffness: 420, damping: 32 };

/** Spring-counts a number to its value on mount/update; instant if reduced-motion. */
function CountUp({ value = 0, decimals = 0 }) {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? value : 0);
  const prev = useRef(0);
  useEffect(() => {
    if (reduce) {
      setN(value);
      prev.current = value;
      return;
    }
    const controls = animate(prev.current, value, {
      duration: 0.7,
      ease: [0.2, 0.8, 0.2, 1],
      onUpdate: (v) => setN(v),
    });
    prev.current = value;
    return () => controls.stop();
  }, [value, reduce]);
  return (
    <>
      {Number(n).toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
    </>
  );
}

/** A compact overview tile: animated number, optional progress bar and subtext. */
function StatCard({ label, value, decimals = 0, unit, suffix, sub, accent = "var(--color-teal)", progress }) {
  return (
    <Card className="p-4">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-soft">{label}</div>
      <div className="mt-1 flex items-end gap-1">
        <span className="stat-number text-3xl leading-none">
          <CountUp value={value} decimals={decimals} />
          {suffix}
        </span>
        {unit && <span className="mb-0.5 text-sm font-semibold text-ink-soft">{unit}</span>}
      </div>
      {progress != null && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line">
          <motion.div
            className="h-full rounded-full"
            style={{ background: accent }}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(Math.max(progress, 0), 1) * 100}%` }}
            transition={{ duration: 0.7, ease: [0.2, 0.8, 0.2, 1] }}
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
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard label="Current weight" value={s.current_weight_kg} decimals={1} unit="kg" sub={`Goal: ${s.goal}`} />
      <StatCard
        label="Target weight"
        value={s.target_weight_kg}
        decimals={1}
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
        value={s.water_ml / 1000}
        decimals={1}
        unit="L"
        progress={s.water_ml / s.water_goal_ml}
        sub={`goal ${(s.water_goal_ml / 1000).toFixed(1)} L`}
      />
      <StatCard
        label="Steps"
        value={s.steps}
        accent="var(--color-volt-press)"
        progress={s.steps / s.step_goal}
        sub={`goal ${s.step_goal.toLocaleString()}`}
      />
      <StatCard
        label="Workouts"
        value={s.workout_completion_pct}
        suffix="%"
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

/** Manual quick-log — the only honest way to fill water/steps/workout without a wearable. */
function TodayCard({ waterGoalMl = 2500, stepGoal = 9000 }) {
  const { data: log } = useTodayLog();
  const update = useUpdateLog();
  const [steps, setSteps] = useState("");
  useEffect(() => {
    if (log) setSteps(String(log.steps ?? 0));
  }, [log]);
  if (!log) return null;

  const water = log.water_ml ?? 0;
  const addWater = (ml) => update.mutate({ water_ml: Math.max(0, water + ml) });
  const saveSteps = () => update.mutate({ steps: Number(steps || 0) });
  const toggleWorkout = () => update.mutate({ workout_done: !log.workout_done });

  return (
    <Card>
      <h3 className="flex items-center gap-2 font-display text-lg font-bold">
        <Flame className="size-4 text-coral" /> Today
      </h3>
      <p className="mt-1 text-sm text-ink-soft">Log it to keep your streak and goals live.</p>

      {/* Water */}
      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-sm">
          <span className="flex items-center gap-1.5 font-medium">
            <Droplets className="size-4 text-teal" /> Water
          </span>
          <span className="text-ink-soft">
            {water} / {waterGoalMl} ml
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-line">
          <div
            className="h-full rounded-full bg-teal transition-[width] duration-500"
            style={{ width: `${Math.min(water / waterGoalMl, 1) * 100}%` }}
          />
        </div>
        <div className="mt-2 flex gap-2">
          <Button variant="outline" className="px-3 py-1.5" onClick={() => addWater(250)}>
            +250 ml
          </Button>
          <Button variant="outline" className="px-3 py-1.5" onClick={() => addWater(500)}>
            +500 ml
          </Button>
          <Button variant="ghost" className="px-3 py-1.5" onClick={() => addWater(-250)}>
            −250
          </Button>
        </div>
      </div>

      {/* Steps */}
      <div className="mt-4">
        <div className="mb-1 flex items-center gap-1.5 text-sm font-medium">
          <Footprints className="size-4 text-volt-press" /> Steps
          <span className="font-normal text-ink-soft">· goal {stepGoal.toLocaleString()}</span>
        </div>
        <div className="flex gap-2">
          <Input
            type="number"
            inputMode="numeric"
            value={steps}
            onChange={(e) => setSteps(e.target.value)}
            onBlur={saveSteps}
          />
          <Button variant="outline" onClick={saveSteps} loading={update.isPending}>
            Save
          </Button>
        </div>
      </div>

      {/* Workout */}
      <Button
        variant={log.workout_done ? "primary" : "outline"}
        className="mt-4 w-full"
        onClick={toggleWorkout}
      >
        <Dumbbell className="size-4" />
        {log.workout_done ? "Workout done ✓" : "Mark workout done"}
      </Button>
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
          <span className="stat-number text-5xl">
            <CountUp value={calories} />
          </span>
          <span className="mb-1 text-sm font-semibold text-ink-soft">kcal / day target</span>
        </div>
      </div>
    </Card>
  );
}

// Pick a food emoji for a meal so the plan reads less like a spreadsheet.
const MEAL_EMOJI = { Breakfast: "🍳", Lunch: "🍛", Dinner: "🍽️", Snack: "🍎" };
const MEAL_TINT = {
  Breakfast: "from-amber/30",
  Lunch: "from-teal/30",
  Dinner: "from-coral/30",
  Snack: "from-volt/40",
};

function WorkoutCard({ workout }) {
  return (
    <Card>
      <h3 className="flex items-center gap-2 font-display text-lg font-bold">
        <Dumbbell className="size-4 text-volt-press" /> Training
      </h3>
      <p className="text-sm text-ink-soft">{workout.split}</p>
      <div className="mt-4 space-y-3">
        {(workout.sessions ?? []).map((s, i) => (
          <div key={i} className="overflow-hidden rounded-[12px] border border-line">
            <div className="flex items-center justify-between bg-gradient-to-r from-volt/20 to-transparent px-3 py-2">
              <span className="flex items-center gap-2 font-semibold">
                <Dumbbell className="size-4 text-volt-press" /> {s.day}
              </span>
              <span className="rounded-full bg-paper px-2 py-0.5 text-xs font-medium text-ink-soft">
                {s.focus}
              </span>
            </div>
            <ul className="space-y-1 p-3">
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
          <div key={i} className="flex gap-3 rounded-[12px] border border-line p-3">
            <div
              className={`grid size-12 shrink-0 place-items-center rounded-[10px] bg-gradient-to-br to-transparent text-2xl ${
                MEAL_TINT[m.name] ?? "from-volt/30"
              }`}
            >
              {MEAL_EMOJI[m.name] ?? "🍴"}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold">{m.name}</span>
                <span className="text-sm text-ink-soft">
                  {m.kcal} kcal · {m.protein_g}g P
                </span>
              </div>
              <p className="mt-0.5 truncate text-sm capitalize text-ink-soft">
                {(m.items ?? []).join(", ")}
              </p>
            </div>
          </div>
        ))}
      </div>
    </Card>
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
          <Button className="mt-5" loading={generate.isPending} onClick={() => generate.mutate()}>
            <Sparkles className="size-4" /> Generate my plan
          </Button>
          {generate.isError && <p className="mt-3 text-sm text-coral">{generate.error.message}</p>}
        </Card>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={spring} className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-ink-soft">
          <span className="rounded-full bg-ink/5 px-2.5 py-1 font-medium">Plan v{plan.version}</span>
          {plan.degraded && (
            <span className="rounded-full bg-amber/20 px-2.5 py-1 font-medium text-amber">fallback</span>
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
        <TodayCard waterGoalMl={summary?.water_goal_ml} stepGoal={summary?.step_goal} />
        {summary && <CoachingEngine engine={summary.engine} agents={summary.agents} />}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <MealsCard nutrition={plan.nutrition ?? {}} />
        <WorkoutCard workout={plan.workout ?? {}} />
      </div>
    </motion.div>
  );
}
