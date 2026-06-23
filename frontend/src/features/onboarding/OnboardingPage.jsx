import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, Card, Field, Input, Select, Spinner } from "../../components/ui.jsx";
import { useProfile, useSaveProfile } from "../profile/profile.api";

const EMPTY = {
  name: "",
  age: 28,
  sex: "male",
  height_cm: 175,
  weight_kg: 75,
  goal: "lose",
  activity_level: "moderate",
  experience: "beginner",
  training_days: 4,
  rate_kg_per_week: 0.5,
  equipment: "",
  dietary_prefs: "",
  allergies: "",
};

const toList = (s) =>
  s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

export default function OnboardingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const isProfileRoute = location.pathname === "/profile";
  const { data: profile, isLoading } = useProfile();
  const save = useSaveProfile();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState(null);

  // prefill from an existing profile when editing
  useEffect(() => {
    if (profile) {
      setForm({
        ...EMPTY,
        ...profile,
        equipment: (profile.equipment ?? []).join(", "),
        dietary_prefs: (profile.dietary_prefs ?? []).join(", "),
        allergies: (profile.allergies ?? []).join(", "),
      });
    }
  }, [profile]);

  const set = (key) => (e) => {
    const v = e.target.type === "number" ? Number(e.target.value) : e.target.value;
    setForm((f) => ({ ...f, [key]: v }));
  };

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    const payload = {
      ...form,
      equipment: toList(form.equipment),
      dietary_prefs: toList(form.dietary_prefs),
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
            <Input type="number" min={13} max={100} required value={form.age} onChange={set("age")} />
          </Field>
          <Field label="Sex">
            <Select value={form.sex} onChange={set("sex")}>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </Select>
          </Field>

          <Field label="Height (cm)">
            <Input type="number" min={50} max={260} required value={form.height_cm} onChange={set("height_cm")} />
          </Field>
          <Field label="Weight (kg)">
            <Input type="number" min={20} max={400} required value={form.weight_kg} onChange={set("weight_kg")} />
          </Field>

          <Field label="Goal">
            <Select value={form.goal} onChange={set("goal")}>
              <option value="lose">Lose fat</option>
              <option value="maintain">Maintain</option>
              <option value="gain">Gain muscle</option>
            </Select>
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
            <Input
              type="number"
              min={0}
              max={7}
              value={form.training_days}
              onChange={set("training_days")}
            />
          </Field>

          <Field label="Target rate (kg / week)" hint="0 = maintain, up to 1.5">
            <Input
              type="number"
              step="0.1"
              min={0}
              max={1.5}
              value={form.rate_kg_per_week}
              onChange={set("rate_kg_per_week")}
            />
          </Field>
          <Field label="Equipment" hint="comma-separated, e.g. dumbbells, barbell">
            <Input value={form.equipment} onChange={set("equipment")} placeholder="dumbbells" />
          </Field>

          <Field label="Dietary preferences" hint="comma-separated">
            <Input value={form.dietary_prefs} onChange={set("dietary_prefs")} placeholder="vegetarian" />
          </Field>
          <Field label="Allergies" hint="comma-separated">
            <Input value={form.allergies} onChange={set("allergies")} placeholder="peanuts" />
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
