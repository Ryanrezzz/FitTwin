import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, Card, Field, Input, Select, Spinner, cn } from "../../components/ui.jsx";
import { useProfile, useSaveProfile } from "../profile/profile.api";

// Numeric fields are kept as STRINGS in form state so the inputs don't fight the
// user (no "089" leading-zero artifact, empty is allowed); we coerce on submit.
const EMPTY = {
  name: "",
  age: "28",
  sex: "male",
  height_cm: "175",
  weight_kg: "75",
  goal: "lose",
  target_weight_kg: "",
  activity_level: "moderate",
  experience: "beginner",
  training_days: "4",
  rate_kg_per_week: "0.5",
  gym_type: "partial",
  equipment: [],
  diet: "nonveg",
  allergies: "",
};

const GYM_TYPES = [
  ["full_gym", "Full gym (commercial)"],
  ["home_gym", "Home gym (well-equipped)"],
  ["partial", "Some equipment"],
  ["bodyweight", "No equipment (bodyweight)"],
];
const EQUIPMENT = [
  ["dumbbells", "Dumbbells"],
  ["barbell", "Barbell"],
  ["resistance_bands", "Resistance bands"],
  ["kettlebells", "Kettlebells"],
  ["pull_up_bar", "Pull-up bar"],
  ["bench", "Bench"],
  ["cable_machine", "Cable machine"],
  ["treadmill", "Treadmill"],
];
const DIETS = [
  ["nonveg", "Non-vegetarian"],
  ["veg", "Vegetarian"],
  ["egg", "Eggetarian"],
  ["vegan", "Vegan"],
];

const NUMERIC = ["age", "height_cm", "weight_kg", "training_days", "rate_kg_per_week"];
const toList = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);

export default function OnboardingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const isProfileRoute = location.pathname === "/profile";
  const { data: profile, isLoading } = useProfile();
  const save = useSaveProfile();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState(null);

  // prefill from an existing profile when editing (numbers -> strings)
  useEffect(() => {
    if (!profile) return;
    setForm({
      ...EMPTY,
      ...profile,
      age: String(profile.age ?? ""),
      height_cm: String(profile.height_cm ?? ""),
      weight_kg: String(profile.weight_kg ?? ""),
      training_days: String(profile.training_days ?? ""),
      rate_kg_per_week: String(profile.rate_kg_per_week ?? ""),
      target_weight_kg:
        profile.target_weight_kg != null ? String(profile.target_weight_kg) : "",
      gym_type: profile.gym_type ?? "partial",
      equipment: profile.equipment ?? [],
      diet: profile.dietary_prefs?.[0] ?? "nonveg",
      allergies: (profile.allergies ?? []).join(", "),
    });
  }, [profile]);

  // store the raw string for every field — never coerce mid-keystroke
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const toggleEquip = (token) =>
    setForm((f) => ({
      ...f,
      equipment: f.equipment.includes(token)
        ? f.equipment.filter((t) => t !== token)
        : [...f.equipment, token],
    }));

  const showEquipment = form.gym_type === "home_gym" || form.gym_type === "partial";

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    const num = (v) => (v === "" || v == null ? undefined : Number(v));
    const payload = {
      name: form.name,
      age: num(form.age),
      sex: form.sex,
      height_cm: num(form.height_cm),
      weight_kg: num(form.weight_kg),
      goal: form.goal,
      target_weight_kg: form.goal === "maintain" ? null : (num(form.target_weight_kg) ?? null),
      activity_level: form.activity_level,
      experience: form.experience,
      gym_type: form.gym_type,
      equipment: showEquipment ? form.equipment : [],
      training_days: num(form.training_days),
      rate_kg_per_week: num(form.rate_kg_per_week),
      dietary_prefs: [form.diet],
      allergies: toList(form.allergies),
    };
    try {
      await save.mutateAsync(payload);
      navigate("/");
    } catch (err) {
      setError(err.message || "Could not save profile");
    }
  }

  if (isLoading) return <Spinner label="Loading profile…" />;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="font-display text-3xl font-extrabold tracking-tight">
        {isProfileRoute ? "Your profile" : "Let's build your twin"}
      </h1>
      <p className="mt-1 text-ink-soft">
        {isProfileRoute
          ? "Update your details — regenerate your plan from the dashboard afterwards."
          : "A few details so the coach can build your nutrition and training plan."}
      </p>

      <Card className="mt-5">
        <form onSubmit={onSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Field label="Name">
              <Input required value={form.name} onChange={set("name")} placeholder="Alex" />
            </Field>
          </div>

          <Field label="Age">
            <Input type="number" inputMode="numeric" min={13} max={100} required value={form.age} onChange={set("age")} />
          </Field>
          <Field label="Sex">
            <Select value={form.sex} onChange={set("sex")}>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </Select>
          </Field>

          <Field label="Height (cm)">
            <Input type="number" inputMode="decimal" min={50} max={260} required value={form.height_cm} onChange={set("height_cm")} />
          </Field>
          <Field label="Weight (kg)">
            <Input type="number" inputMode="decimal" min={20} max={400} required value={form.weight_kg} onChange={set("weight_kg")} />
          </Field>

          <Field label="Goal">
            <Select value={form.goal} onChange={set("goal")}>
              <option value="lose">Lose fat</option>
              <option value="maintain">Maintain</option>
              <option value="gain">Gain muscle</option>
            </Select>
          </Field>
          <Field
            label="Goal weight (kg)"
            hint={form.goal === "maintain" ? "Not needed for maintain" : "Your target weight"}
          >
            <Input
              type="number"
              inputMode="decimal"
              step="0.1"
              min={20}
              max={400}
              disabled={form.goal === "maintain"}
              value={form.goal === "maintain" ? "" : form.target_weight_kg}
              onChange={set("target_weight_kg")}
              placeholder="e.g. 74"
            />
          </Field>

          <Field label="Activity level">
            <Select value={form.activity_level} onChange={set("activity_level")}>
              <option value="sedentary">Sedentary</option>
              <option value="light">Light</option>
              <option value="moderate">Moderate</option>
              <option value="active">Active</option>
              <option value="very_active">Very active</option>
            </Select>
          </Field>
          <Field label="Experience">
            <Select value={form.experience} onChange={set("experience")}>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </Select>
          </Field>

          <Field label="Training days / week">
            <Input type="number" inputMode="numeric" min={0} max={7} value={form.training_days} onChange={set("training_days")} />
          </Field>
          <Field label="Target rate (kg / week)" hint="0 = maintain, up to 1.5">
            <Input type="number" inputMode="decimal" step="0.1" min={0} max={1.5} value={form.rate_kg_per_week} onChange={set("rate_kg_per_week")} />
          </Field>

          {/* ── Where do you train? ── */}
          <div className="sm:col-span-2">
            <Field label="Where do you train?">
              <Select value={form.gym_type} onChange={set("gym_type")}>
                {GYM_TYPES.map(([v, label]) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>
            {showEquipment ? (
              <div className="mt-2">
                <span className="mb-1.5 block text-xs text-ink-soft/80">
                  Tap what you have available:
                </span>
                <div className="flex flex-wrap gap-2">
                  {EQUIPMENT.map(([token, label]) => {
                    const on = form.equipment.includes(token);
                    return (
                      <button
                        type="button"
                        key={token}
                        onClick={() => toggleEquip(token)}
                        className={cn(
                          "rounded-full border px-3 py-1.5 text-sm font-medium transition active:scale-95",
                          on
                            ? "border-volt-press bg-volt text-ink"
                            : "border-line bg-bone text-ink-soft hover:border-ink/30",
                        )}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <p className="mt-2 text-xs text-ink-soft/80">
                {form.gym_type === "full_gym"
                  ? "We'll assume full access to machines and free weights."
                  : "We'll build a bodyweight program — no equipment needed."}
              </p>
            )}
          </div>

          {/* ── Diet ── */}
          <Field label="Dietary preference">
            <Select value={form.diet} onChange={set("diet")}>
              {DIETS.map(([v, label]) => (
                <option key={v} value={v}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Allergies" hint="comma-separated, e.g. peanuts, lactose">
            <Input value={form.allergies} onChange={set("allergies")} placeholder="none" />
          </Field>

          {error && <p className="text-sm text-coral sm:col-span-2">{error}</p>}

          <div className="sm:col-span-2">
            <Button type="submit" loading={save.isPending} className="w-full">
              {isProfileRoute ? "Save changes" : "Save & continue"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
