import { Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Flame, RefreshCw, Sparkles, Utensils } from "lucide-react";
import { Button, Card, Spinner } from "../../components/ui.jsx";
import { useProfile } from "../profile/profile.api";
import { useActivePlan, useGeneratePlan } from "./plan.api";

const spring = { type: "spring", stiffness: 420, damping: 32 };

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
    </motion.div>
  );
}
