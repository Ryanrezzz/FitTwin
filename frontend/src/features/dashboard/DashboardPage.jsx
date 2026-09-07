import { useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { animate, motion, useReducedMotion } from "framer-motion";
import {
  Check,
  Droplets,
  Dumbbell,
  Flame,
  Footprints,
  Plus,
  RefreshCw,
  Sparkles,
  TrendingDown,
  Utensils,
} from "lucide-react";
import { Button, Card, Input, Spinner, cn } from "../../components/ui.jsx";
import { useProfile } from "../profile/profile.api";
import { useActivePlan, useDashboardSummary, useGeneratePlan } from "./plan.api";
import { useLogHistory, useTodayLog, useUpdateLog } from "./logs.api";
import { useResetRotations, useRotateMeal } from "./meals.api";
import { useLogWeight, useWeightSeries } from "./progress.api";

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

/** An overview tile.
 *
 * Deliberately dense: all eight metrics matter to a daily user, so the fix for
 * "the whole first screen is statistics" is a shorter tile, not fewer of them.
 * Trimmed padding/type takes each tile from ~165px to ~95px — the same eight
 * numbers in roughly half a phone screen.
 */
function StatCard({ label, value, decimals = 0, unit, suffix, sub, accent = "var(--color-teal)", progress }) {
  return (
    <Card className="p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-soft">{label}</div>
      <div className="mt-0.5 flex items-end gap-1">
        <span className="stat-number text-2xl leading-none">
          <CountUp value={value} decimals={decimals} />
          {suffix}
        </span>
        {unit && <span className="mb-px text-xs font-semibold text-ink-soft">{unit}</span>}
      </div>
      {progress != null && (
        <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-line">
          <motion.div
            className="h-full rounded-full"
            style={{ background: accent }}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(Math.max(progress, 0), 1) * 100}%` }}
            transition={{ duration: 0.7, ease: [0.2, 0.8, 0.2, 1] }}
          />
        </div>
      )}
      {sub && <div className="mt-1 truncate text-[11px] text-ink-soft">{sub}</div>}
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
        unit={s.streak_days === 1 ? "day" : "days"}
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

/** The page header: who this is, and what today's target is.
 *
 * This used to be a tall card sitting *below* the logging cards, which left the
 * greeting stranded in the middle of a phone screen — it reads as a mistake,
 * because a name is a header, not a mid-page element. Folding the plan chip and
 * the Regenerate action in here keeps the name first without pushing the day's
 * inputs below the fold.
 */
function TwinHeader({ name, goal, calories, version, degraded, onRegenerate, regenerating }) {
  return (
    <Card className="relative overflow-hidden">
      <div className="pointer-events-none absolute -right-12 -top-12 size-44 rounded-full bg-volt/40 blur-2xl" />
      <div className="pointer-events-none absolute -right-4 bottom--6 size-24 rounded-full bg-teal/25 blur-2xl" />

      <div className="relative flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs font-medium text-ink-soft">
            <Sparkles className="size-3.5 text-volt-press" /> Your digital twin
          </div>
          <h1 className="mt-1 font-display text-3xl font-extrabold leading-tight tracking-tight">
            Hey {name || "athlete"} 👋
          </h1>
          <p className="mt-1 text-sm text-ink-soft">
            Goal <span className="font-semibold text-ink">{goal}</span>
            {" · "}
            <span className="stat-number text-ink">
              <CountUp value={calories} />
            </span>{" "}
            kcal / day
          </p>
        </div>

        {/* One row on a phone (stacking these wasted ~50px of dead space);
            top-right on wider screens. */}
        <div className="flex w-full shrink-0 flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
          <span className="rounded-full bg-ink/5 px-2.5 py-1 text-xs font-medium text-ink-soft">
            Plan v{version}
          </span>
          {degraded && (
            <span className="rounded-full bg-amber/20 px-2.5 py-1 text-xs font-medium text-amber">
              fallback
            </span>
          )}
          {/* Rebuilding discards the current plan, so it stays a quiet utility. */}
          <Button
            variant="ghost"
            className="ml-auto px-2.5 py-1.5 text-xs sm:ml-0"
            loading={regenerating}
            onClick={onRegenerate}
            title="Rebuild your plan from your current profile"
          >
            <RefreshCw className="size-3.5" /> Regenerate plan
          </Button>
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
// Keyed on the backend's `slot`, not the display name — the label changed once
// ("Snack" -> "Evening Snack") and a name-keyed map silently lost its colour.
const MEAL_TINT = {
  breakfast: "from-amber/30",
  lunch: "from-teal/30",
  snack: "from-volt/40",
  dinner: "from-coral/30",
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

/** Bodyweight trend + today's weigh-in.
 *
 * Until this existed, "current weight" was the number typed at onboarding and
 * could never change, so the weight card, weeks-to-goal and plateau detection
 * were all reading a constant.
 */
function WeightSparkline({ points, goalKg }) {
  if (points.length < 2) return null;
  const w = 260;
  const h = 64;
  const pad = 6;
  const values = points.map((p) => p.weight_kg);
  const lo = Math.min(...values, goalKg ?? Infinity);
  const hi = Math.max(...values, goalKg ?? -Infinity);
  const span = hi - lo || 1;
  const x = (i) => pad + (i * (w - pad * 2)) / (points.length - 1);
  const y = (v) => pad + (1 - (v - lo) / span) * (h - pad * 2);
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.weight_kg).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.length - 1).toFixed(1)},${h - pad} L${x(0).toFixed(1)},${h - pad} Z`;
  const last = points[points.length - 1];

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="mt-3 w-full"
      role="img"
      aria-label={`Weight trend, latest ${last.weight_kg} kg`}
    >
      <path d={area} fill="var(--color-teal)" opacity="0.12" />
      <path d={line} fill="none" stroke="var(--color-teal)" strokeWidth="2" strokeLinejoin="round" />
      <circle cx={x(points.length - 1)} cy={y(last.weight_kg)} r="3.5" fill="var(--color-teal)" />
    </svg>
  );
}

function WeightCard({ goalKg }) {
  const { data, isLoading } = useWeightSeries();
  const logWeight = useLogWeight();
  const [value, setValue] = useState("");

  const entries = data?.entries ?? [];
  // API returns newest-first; a chart reads oldest-left.
  const points = [...entries].reverse();
  const change = data?.change_kg;

  const save = () => {
    const kg = Number(value);
    if (!kg || kg <= 20 || kg >= 400) return;
    logWeight.mutate(kg, { onSuccess: () => setValue("") });
  };

  return (
    <Card>
      <h3 className="flex items-center gap-2 font-display text-lg font-bold">
        <TrendingDown className="size-4 text-teal" /> Weight
      </h3>

      {isLoading ? (
        <div className="mt-4"><Spinner label="Loading trend…" /></div>
      ) : entries.length === 0 ? (
        <p className="mt-1 text-sm text-ink-soft">
          Log your first weigh-in to start tracking progress toward your goal.
        </p>
      ) : (
        <>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="stat-number text-3xl">{data.latest_kg}</span>
            <span className="text-sm text-ink-soft">kg</span>
            {change != null && change !== 0 && (
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-semibold",
                  change < 0 ? "bg-teal/15 text-teal" : "bg-coral/15 text-coral",
                )}
              >
                {change > 0 ? "+" : ""}
                {change} kg
              </span>
            )}
            {goalKg != null && (
              <span className="ml-auto text-xs text-ink-soft">goal {goalKg} kg</span>
            )}
          </div>
          <WeightSparkline points={points} goalKg={goalKg} />
          <p className="text-xs text-ink-soft">
            {data.days_tracked} weigh-in{data.days_tracked === 1 ? "" : "s"} recorded
          </p>
        </>
      )}

      <div className="mt-4 flex gap-2">
        <Input
          type="number"
          inputMode="decimal"
          step="0.1"
          placeholder="today's weight (kg)"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && save()}
          aria-label="Today's weight in kilograms"
        />
        <Button onClick={save} loading={logWeight.isPending} disabled={!value}>
          Log
        </Button>
      </div>
      {logWeight.isError && (
        <p className="mt-2 text-xs text-coral">
          Could not save that weight. Enter a value between 20 and 400 kg.
        </p>
      )}
    </Card>
  );
}

function MealRow({ meal, index, onRotate, rotating }) {
  const items = meal.items ?? [];
  return (
    <motion.div
      className="rounded-[12px] border border-line p-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, ...spring }}
    >
      <div className="flex gap-3">
        <div
          className={`grid size-12 shrink-0 place-items-center rounded-[10px] bg-gradient-to-br to-transparent text-2xl ${
            MEAL_TINT[meal.slot] ?? "from-volt/30"
          }`}
        >
          {foodEmoji(items)}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
              {meal.name}
            </span>
            <span className="stat-number shrink-0 text-sm">
              {meal.kcal} kcal · {meal.protein_g}g P
            </span>
          </div>

          {meal.dish && <p className="mt-0.5 font-semibold leading-snug">{meal.dish}</p>}

          {/* Portions wrap as chips instead of truncating — they are the actual
              instruction ("dal 60g", "3 x roti"), so clipping them loses the point. */}
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {items.map((item, i) => (
              <li
                key={i}
                className="rounded-full bg-ink/[.04] px-2 py-0.5 text-xs text-ink-soft"
              >
                {item}
              </li>
            ))}
          </ul>
        </div>

        {onRotate && (
          <button
            type="button"
            onClick={() => onRotate(meal.slot)}
            disabled={rotating}
            title={`Swap ${meal.name.toLowerCase()} for a different dish`}
            aria-label={`Swap ${meal.name} for a different dish`}
            className="grid size-9 shrink-0 place-items-center self-start rounded-[10px] border border-line
                       text-ink-soft transition hover:border-volt-press hover:text-ink
                       disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-volt"
          >
            <RefreshCw className={cn("size-4", rotating && "animate-spin")} />
          </button>
        )}
      </div>
    </motion.div>
  );
}

function MealsCard({ meals = [], canRotate = false }) {
  const rotate = useRotateMeal();
  const reset = useResetRotations();
  const [pending, setPending] = useState(null);

  if (meals.length === 0) return null;
  const today = WEEKDAY[(new Date().getDay() + 6) % 7]; // JS Sun=0 -> Mon-first
  const totalKcal = meals.reduce((sum, m) => sum + (m.kcal ?? 0), 0);
  const totalProtein = meals.reduce((sum, m) => sum + (m.protein_g ?? 0), 0);

  // Only offer rotation when the meals came from the catalog (they carry a
  // `slot`); a legacy plan's meal_plan has no slot to rotate.
  const rotatable = canRotate && meals.every((m) => m.slot);

  async function handleRotate(slot) {
    setPending(slot);
    try {
      await rotate.mutateAsync(slot);
    } finally {
      setPending(null);
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 font-display text-lg font-bold">
          <Utensils className="size-4 text-teal" /> Today's meals
        </h3>
        <div className="flex items-center gap-2">
          {rotatable && (
            <button
              type="button"
              onClick={() => reset.mutate()}
              disabled={reset.isPending}
              className="text-xs font-semibold text-ink-soft underline-offset-2 hover:text-ink hover:underline
                         disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-volt"
            >
              Reset
            </button>
          )}
          <span className="rounded-full bg-teal/15 px-2.5 py-1 text-xs font-semibold text-teal">
            {today}
          </span>
        </div>
      </div>

      {rotatable && (
        <p className="mt-1 text-xs text-ink-soft">
          Not in the mood for something? Swap any meal — the day stays on target.
        </p>
      )}

      <div className="mt-4 space-y-3">
        {meals.map((m, i) => (
          <MealRow
            key={m.slot ?? i}
            meal={m}
            index={i}
            onRotate={rotatable ? handleRotate : null}
            rotating={pending === m.slot}
          />
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-line pt-3 text-sm">
        <span className="text-ink-soft">Day total</span>
        <span className="stat-number">
          {totalKcal} kcal · {totalProtein}g protein
        </span>
      </div>
    </Card>
  );
}

/** Shown only while a new user's day is completely empty.
 *
 * A freshly-generated plan renders every tile as a zero, which reads as "this
 * app is broken" rather than "you haven't started yet". This says which single
 * action turns the zeros into progress, then disappears for good once anything
 * is logged.
 */
function FirstRunNudge({ s }) {
  const untouched =
    !s.water_ml && !s.steps && !s.workouts_done && !s.streak_days &&
    s.calories_remaining === s.calorie_target;
  if (!untouched) return null;
  return (
    <Card className="border-volt-press/40 bg-volt/[.07] p-4">
      <div className="flex items-start gap-3">
        <Sparkles className="mt-0.5 size-4 shrink-0 text-ink" />
        <div>
          <p className="text-sm font-semibold">Your plan is ready — nothing logged yet.</p>
          <p className="mt-0.5 text-sm text-ink-soft">
            Log a glass of water or today&apos;s weight below and these numbers start moving.
          </p>
        </div>
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
      {/* Header and macros read as one unit: who you are, and the split you're
          aiming at. Side by side on desktop, stacked on a phone. */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TwinHeader
            name={profile.name}
            goal={profile.goal}
            calories={plan.calorie_target}
            version={plan.version}
            degraded={plan.degraded}
            onRegenerate={() => generate.mutate()}
            regenerating={generate.isPending}
          />
        </div>
        <Card className="flex flex-col justify-center">
          <h3 className="font-display text-base font-bold">Daily macros</h3>
          <div className="mt-3">
            <MacroSplit macros={plan.macros} />
          </div>
        </Card>
      </div>

      {summary && <FirstRunNudge s={summary} />}
      {summary && <OverviewCards s={summary} />}

      <WeekStrip streak={summary?.streak_days ?? 0} />

      {/* Logging sits high: someone opening the app wants to DO something. */}
      <div className="grid gap-4 lg:grid-cols-2">
        <TodayCard waterGoalMl={summary?.water_goal_ml} stepGoal={summary?.step_goal} />
        <WeightCard goalKg={summary?.target_weight_kg} />
      </div>

      {/* Meals get the full width: portions are listed per item, so a half
          column would wrap every dish onto three lines. */}
      <MealsCard
        meals={summary?.today_meals ?? plan.nutrition?.meal_plan ?? []}
        canRotate={Boolean(summary?.today_meals?.length)}
      />

      <WorkoutCard workout={plan.workout ?? {}} />
    </motion.div>
  );
}
