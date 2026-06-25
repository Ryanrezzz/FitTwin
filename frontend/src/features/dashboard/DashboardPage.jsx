import { useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { animate, motion, useReducedMotion } from "framer-motion";
import { Check, Droplets, Dumbbell, Flame, Footprints, Plus, RefreshCw, Sparkles, Utensils } from "lucide-react";
import { Button, Card, Input, Spinner, cn } from "../../components/ui.jsx";
import { useProfile } from "../profile/profile.api";
import { useActivePlan, useDashboardSummary, useGeneratePlan } from "./plan.api";
import { useLogHistory, useTodayLog, useUpdateLog } from "./logs.api";

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

const DOW = ["S", "M", "T", "W", "T", "F", "S"]; // JS getDay(): Sun=0
const isoLocal = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** Mini activity calendar — the last 7 days. Days roll over automatically by date. */
function WeekStrip({ streak = 0 }) {
  const { data: history = [] } = useLogHistory(7);
  const byDate = Object.fromEntries((history ?? []).map((h) => [h.date, h]));
  const todayIso = isoLocal(new Date());
  const days = [...Array(7)].map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i)); // oldest → today
    const iso = isoLocal(d);
    const log = byDate[iso];
    return {
      iso,
      dow: DOW[d.getDay()],
      num: d.getDate(),
      workout: !!log?.workout_done,
      active: !!(log && (log.workout_done || log.steps || log.water_ml || log.calories)),
      today: iso === todayIso,
    };
  });
  return (
    <Card>
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-display text-lg font-bold">
          <Flame className="size-4 text-coral" /> This week
        </h3>
        <span className="rounded-full bg-coral/15 px-2.5 py-1 text-xs font-semibold text-coral">
          🔥 {streak}-day streak
        </span>
      </div>
      <div className="mt-4 grid grid-cols-7 gap-2">
        {days.map((d) => (
          <div key={d.iso} className="flex flex-col items-center gap-1">
            <span className="text-[11px] font-medium text-ink-soft">{d.dow}</span>
            <div
              className={cn(
                "grid size-10 place-items-center rounded-full border text-sm font-semibold transition",
                d.workout
                  ? "border-volt-press bg-volt text-ink"
                  : d.active
                    ? "border-teal/40 bg-teal/15 text-ink"
                    : "border-line bg-bone text-ink-soft",
                d.today && "ring-2 ring-volt ring-offset-2 ring-offset-paper",
              )}
            >
              {d.workout ? <Check className="size-4" /> : d.num}
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-ink-soft">
        Days roll over automatically — just log as you go. ✓ = workout done · filled = active day.
      </p>
    </Card>
  );
}

/** Manual quick-log — the only honest way to fill water/steps/food without a wearable. */
function TodayCard({ waterGoalMl = 2500, stepGoal = 9000 }) {
  const { data: log } = useTodayLog();
  const update = useUpdateLog();
  const [steps, setSteps] = useState("");
  const [kcal, setKcal] = useState("");
  const [protein, setProtein] = useState("");
  useEffect(() => {
    if (log) setSteps(String(log.steps ?? 0));
  }, [log]);
  if (!log) return null;

  const water = log.water_ml ?? 0;
  const addWater = (ml) => update.mutate({ water_ml: Math.max(0, water + ml) });
  const saveSteps = () => update.mutate({ steps: Number(steps || 0) });
  const toggleWorkout = () => update.mutate({ workout_done: !log.workout_done });
  const logFood = () => {
    const c = Number(kcal || 0);
    const p = Number(protein || 0);
    if (!c && !p) return;
    update.mutate({
      calories: (log.calories ?? 0) + c,
      protein_g: (log.protein_g ?? 0) + p,
    });
    setKcal("");
    setProtein("");
  };

  return (
    <Card>
      <h3 className="flex items-center gap-2 font-display text-lg font-bold">
        <Flame className="size-4 text-coral" /> Today
      </h3>
      <p className="mt-1 text-sm text-ink-soft">Log it to keep your streak and goals live.</p>

      {/* Food → drives "Calories left" / "Protein left" */}
      <div className="mt-4">
        <div className="mb-1 flex items-center gap-1.5 text-sm font-medium">
          <Utensils className="size-4 text-coral" /> Log food
          <span className="font-normal text-ink-soft">
            · eaten {log.calories ?? 0} kcal / {Math.round(log.protein_g ?? 0)}g P
          </span>
        </div>
        <div className="flex gap-2">
          <Input
            type="number"
            inputMode="numeric"
            placeholder="kcal"
            value={kcal}
            onChange={(e) => setKcal(e.target.value)}
          />
          <Input
            type="number"
            inputMode="numeric"
            placeholder="protein g"
            value={protein}
            onChange={(e) => setProtein(e.target.value)}
          />
          <Button variant="outline" onClick={logFood} loading={update.isPending}>
            <Plus className="size-4" /> Add
          </Button>
        </div>
      </div>

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

// Pick a food emoji from the meal's main item so each card reads like a dish.
const FOOD_EMOJI = [
  [/oat/, "🥣"], [/poha|upma|khichdi/, "🍚"], [/idli|dosa/, "🥞"], [/egg/, "🥚"],
  [/paneer|tofu|curd|dahi|yogurt|milk/, "🧀"], [/chicken|keema/, "🍗"], [/fish/, "🐟"],
  [/rajma|chana|dal|lentil|sprout|soy|chickpea/, "🍲"], [/roti|chilla|sandwich/, "🫓"],
  [/rice|quinoa/, "🍚"], [/banana|fruit/, "🍌"], [/salad|palak|spinach|bhindi|sabzi|veg|cucumber/, "🥗"],
  [/peanut|whey|shake|protein/, "🥜"], [/potato/, "🥔"],
];
const foodEmoji = (items = []) => {
  const text = items.join(" ").toLowerCase();
  for (const [re, emoji] of FOOD_EMOJI) if (re.test(text)) return emoji;
  return "🍴";
};
const MEAL_TINT = {
  Breakfast: "from-amber/30",
  Lunch: "from-teal/30",
  Dinner: "from-coral/30",
  Snack: "from-volt/40",
};

// Muscle groups a split day trains, and a best-guess target per exercise name.
const FOCUS_MUSCLES = {
  push: "Chest · Shoulders · Triceps",
  pull: "Back · Biceps",
  legs: "Quads · Hamstrings · Glutes · Calves",
  upper: "Chest · Back · Shoulders · Arms",
  lower: "Quads · Hamstrings · Glutes",
  full: "Full body",
};
const EX_MUSCLE = [
  [/squat|leg press|lunge|split squat/i, "Quads"],
  [/deadlift|rdl|romanian|hip thrust|glute|good-?morning|bridge/i, "Posterior"],
  [/row|pulldown|pull-?up|lat|inverted/i, "Back"],
  [/overhead|ohp|pike|shoulder/i, "Shoulders"],
  [/bench|push-?up|chest|incline|dip|press/i, "Chest"],
  [/curl/i, "Biceps"],
  [/triceps|pushdown/i, "Triceps"],
  [/calf/i, "Calves"],
  [/plank|core|superman/i, "Core"],
];
const exMuscle = (name = "") => {
  for (const [re, m] of EX_MUSCLE) if (re.test(name)) return m;
  return "Compound";
};

/** Pro-style program view: pick a day, see its focus + target muscles + exercises. */
function WorkoutCard({ workout }) {
  const sessions = workout.sessions ?? [];
  const [active, setActive] = useState(0);
  if (sessions.length === 0) return null;
  const idx = Math.min(active, sessions.length - 1);
  const s = sessions[idx];
  const focus = (s.focus || "").toLowerCase();
  const note = s.exercises?.[0]?.load_guidance;

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 font-display text-lg font-bold">
          <Dumbbell className="size-4 text-volt-press" /> Training
        </h3>
        <span className="rounded-full bg-ink/5 px-2.5 py-1 text-xs font-medium text-ink-soft">
          {workout.split}
        </span>
      </div>

      {/* day selector */}
      <div className="mt-3 flex flex-wrap gap-2">
        {sessions.map((sess, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setActive(i)}
            className={cn(
              "rounded-full px-3 py-1.5 text-sm font-medium transition active:scale-95",
              i === idx
                ? "bg-volt text-ink"
                : "border border-line bg-bone text-ink-soft hover:border-ink/30",
            )}
          >
            {sess.day} · {sess.focus}
          </button>
        ))}
      </div>

      {/* selected day */}
      <motion.div
        key={idx}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring}
        className="mt-4"
      >
        <div className="mb-2 flex flex-wrap items-baseline gap-x-2">
          <span className="font-display text-lg font-bold">{s.focus}</span>
          <span className="text-sm text-ink-soft">{FOCUS_MUSCLES[focus] ?? ""}</span>
        </div>
        <ul className="space-y-1.5">
          {(s.exercises ?? []).map((ex, j) => (
            <motion.li
              key={j}
              className="flex items-center justify-between gap-2 rounded-[10px] border border-line px-3 py-2"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: j * 0.05, ...spring }}
            >
              <span className="flex min-w-0 items-center gap-2.5">
                <span className="grid size-7 shrink-0 place-items-center rounded-md bg-volt/20 text-xs font-bold text-ink">
                  {j + 1}
                </span>
                <span className="min-w-0">
                  <span className="block truncate font-medium">{ex.name}</span>
                  <span className="text-xs text-ink-soft">{exMuscle(ex.name)}</span>
                </span>
              </span>
              <span className="shrink-0 rounded-full bg-ink/5 px-2.5 py-1 text-sm font-semibold tabular-nums">
                {ex.sets} × {ex.reps}
              </span>
            </motion.li>
          ))}
        </ul>
        {note && (
          <p className="mt-3 flex items-start gap-1.5 text-xs text-ink-soft">
            <span>📈</span> {note}
          </p>
        )}
      </motion.div>
    </Card>
  );
}

const WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function MealsCard({ meals = [] }) {
  if (meals.length === 0) return null;
  const today = WEEKDAY[(new Date().getDay() + 6) % 7]; // JS Sun=0 → Mon-first
  return (
    <Card>
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-display text-lg font-bold">
          <Utensils className="size-4 text-teal" /> Today's meals
        </h3>
        <span className="rounded-full bg-teal/15 px-2.5 py-1 text-xs font-semibold text-teal">
          {today}
        </span>
      </div>
      <div className="mt-4 space-y-3">
        {meals.map((m, i) => (
          <motion.div
            key={i}
            className="flex gap-3 rounded-[12px] border border-line p-3"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06, ...spring }}
          >
            <div
              className={`grid size-12 shrink-0 place-items-center rounded-[10px] bg-gradient-to-br to-transparent text-2xl ${
                MEAL_TINT[m.name] ?? "from-volt/30"
              }`}
            >
              {foodEmoji(m.items)}
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
          </motion.div>
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

      <WeekStrip streak={summary?.streak_days ?? 0} />

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
        <MealsCard meals={summary?.today_meals ?? plan.nutrition?.meal_plan ?? []} />
      </div>

      <WorkoutCard workout={plan.workout ?? {}} />
    </motion.div>
  );
}
